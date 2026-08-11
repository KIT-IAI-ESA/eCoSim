from __future__ import annotations

import threading
from abc import abstractmethod
from dataclasses import InitVar, dataclass, field
from typing import Callable, assert_never, override
from uuid import uuid4

import dask.distributed as distributed
from ecosim_common.communication.communication_protocol import CommunicationProtocol


@dataclass(frozen=True)
class ParallelEvent:
    """Uniform wrapper over threading.Event and dask.distributed.Event."""

    @staticmethod
    def for_communication_protocol(
        communication_protocol: CommunicationProtocol,
        dask_name: str | None = None,
    ) -> ParallelEvent:
        match communication_protocol:
            case CommunicationProtocol.DASK:
                return ParallelEvent.dask(dask_name=dask_name)
            case CommunicationProtocol.TCP_SOCKET:
                return ParallelEvent.thread()
            case _:
                assert_never(communication_protocol)

    @staticmethod
    def dask(
        dask_name: str | None = None,
        init_set: bool = False,
    ) -> ParallelEvent:
        return ParallelEventDask.for_name(
            name=dask_name or f"parallel_event_dask_{uuid4()}",
            init_set=init_set,
        )

    @staticmethod
    def thread(init_set: bool = False) -> ParallelEvent:
        return ParallelEventThread(init_set=init_set)

    @abstractmethod
    def _event(self) -> threading.Event | distributed.Event:
        pass

    def set(self) -> None:
        # actually, the dask implementation returns something
        self._event().set()

    def clear(self) -> None:
        # actually, the dask implementation returns something
        self._event().clear()

    def is_set(self) -> bool:
        return self._event().is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event().wait(timeout=timeout)

    def set_state(self, state: bool) -> None:
        self._event().set() if state else self._event().clear()


@dataclass(frozen=True)
class ParallelEventDask(ParallelEvent):
    init_set: InitVar[bool]

    _name: str = field()
    _dask_event: distributed.Event = field(compare=False, repr=False)

    @staticmethod
    def for_name(
        name: str,
        init_set: bool = False,
    ) -> ParallelEventDask:
        return ParallelEventDask(
            _name=name,
            _dask_event=distributed.Event(name=name),
            init_set=init_set,
        )

    def __post_init__(self, init_set: bool) -> None:
        if init_set:
            self._dask_event.set()

    @override
    def _event(self) -> threading.Event | distributed.Event:
        return self._dask_event

    def __reduce__(self) -> tuple[Callable[[str], ParallelEventDask], tuple[str]]:
        return (self.__class__.for_name, (self._name,))


@dataclass(frozen=True)
class ParallelEventThread(ParallelEvent):
    init_set: InitVar[bool]

    _thread_event: threading.Event = field(default_factory=threading.Event)

    def __post_init__(self, init_set: bool) -> None:
        if init_set:
            self._thread_event.set()

    @override
    def _event(self) -> threading.Event | distributed.Event:
        return self._thread_event
