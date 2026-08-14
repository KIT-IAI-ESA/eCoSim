from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from queue import Empty, Queue
from typing import Any, Generic, Iterable, TypeVar, assert_never, cast, override

import distributed
from distributed import Client
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.logger.with_silenced_logger import silenced_logger
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType

T = TypeVar("T")

_logger = ESPLogger("ESPQueue")


class ESPQueue(ABC, Generic[T]):
    """
    A wrapper around different kind of queues (FIFO).

    ATTENTION: Do not assume 'qsize' is still accurate by the time you act on it -- with multiple
               producers/consumers it is only a hint.
    """

    @staticmethod
    def of_communication_protocol(
        communication_protocol: CommunicationProtocol,
        data: Iterable[T] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
        maxsize: int = 0,
    ) -> ESPQueue[T]:
        return ESPQueue.of_type(
            queue_type=ESPStructureType.default_for_communication_protocol(communication_protocol),
            data=data,
            dask_name=dask_name,
            dask_client=dask_client,
            maxsize=maxsize,
        )

    @staticmethod
    def of_type(
        queue_type: ESPStructureType,
        data: Iterable[T] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
        maxsize: int = 0,
    ) -> ESPQueue[T]:
        match queue_type:
            case ESPStructureType.SIMPLE:
                return ThreadESPQueue(
                    data=data,
                )
            case ESPStructureType.DASK_VARIABLE:
                return DaskESPQueue(
                    data=data,
                    dask_name=dask_name,
                    dask_client=dask_client,
                    maxsize=maxsize,
                )
            case ESPStructureType.THREAD:
                return ThreadESPQueue(
                    data=data,
                )
            case _:
                assert_never(queue_type)

    @abstractmethod
    def push(self, value: T) -> None:
        pass

    @abstractmethod
    def pop(self, timeout: float | None = None) -> T:
        """Raises Empty (queue.Empty) if nothing is available within 'timeout'."""

    @abstractmethod
    def qsize(self) -> int:
        pass

    def push_many(self, values: Iterable[T]) -> None:
        for value in values:
            self.push(value)

    def pop_or_none(self, timeout: float | None = None) -> T | None:
        try:
            return self.pop(timeout=timeout)
        except Empty:
            return None
        except TimeoutError:
            return None

    def pop_all(self) -> list[T]:
        items: list[T] = []
        while (item := self.pop_or_none(timeout=0)) is not None:
            items.append(item)
        return items

    def clear(self) -> None:
        self.pop_all()

    def __len__(self) -> int:
        return self.qsize()

    def __bool__(self) -> bool:
        return self.qsize() > 0


class DaskESPQueue(ESPQueue[T]):
    """
    ATTENTION: the underlying 'distributed.Queue' is created lazily.

    'distributed.Queue.__init__' issues a blocking 'queue_create' call to the scheduler, and its '__reduce__'
    re-runs '__init__' - so every unpickling of an object holding a queue used to cost a scheduler round-trip.
    Since these queues travel inside pickled callbacks, only the name is carried and the handle is created on
    first use.
    """

    def __init__(
        self,
        data: Iterable[T] | None = None,
        dask_name: str | None = None,
        dask_client: Client | None = None,
        maxsize: int = 0,
    ) -> None:
        self._name = dask_name or f"esp_queue_{uuid.uuid4()}"
        self._maxsize = maxsize
        self._client = dask_client
        self._queue: distributed.Queue | None = None
        for value in data or []:
            self.push(value)

    @property
    def _dask_queue(self) -> distributed.Queue:
        if self._queue is None:
            self._queue = distributed.Queue(
                name=self._name,
                client=self._client,
                maxsize=self._maxsize,
            )
        return self._queue

    def __getstate__(self) -> dict[str, Any]:
        # deliberately without '_queue' and '_client': both are rebuilt lazily in the receiving process
        return {"_name": self._name, "_maxsize": self._maxsize}

    def __setstate__(self, state: dict[str, Any]) -> None:
        self._name = state["_name"]
        self._maxsize = state["_maxsize"]
        self._client = None
        self._queue = None

    @override
    def push(self, value: T) -> None:
        self._dask_queue.put(value)

    @override
    def pop(self, timeout: float | None = None) -> T:
        with silenced_logger("distributed.core"):
            return cast(T, self._dask_queue.get(timeout=timeout))

    @override
    def qsize(self) -> int:
        return self._dask_queue.qsize()


class ThreadESPQueue(ESPQueue[T]):
    def __init__(
        self,
        data: Iterable[T] | None = None,
    ) -> None:
        self._internal_queue: Queue[T] = Queue(maxsize=0)
        for value in data or []:
            self._internal_queue.put(value)

    @override
    def push(self, value: T) -> None:
        self._internal_queue.put(value)

    @override
    def pop(self, timeout: float | None = None) -> T:
        try:
            return self._internal_queue.get(
                block=True,
                timeout=timeout,
            )
        except Empty:
            raise TimeoutError()

    @override
    def qsize(self) -> int:
        return self._internal_queue.qsize()
