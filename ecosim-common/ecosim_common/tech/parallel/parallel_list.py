from __future__ import annotations

import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Iterator, List, assert_never

from dask.distributed import Variable
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.with_silenced_logger import silenced_logger
from ecosim_common.tech.parallel.concurrency_type import ConcurrencyType
from ecosim_common.tech.parallel.parallel_lock import ParallelLock


@dataclass
class ParallelList[T]:
    _parallel_lock: ParallelLock = field()
    _concurrency_type: ConcurrencyType = field()

    _thread_list: List[T] = field(default_factory=list)
    _dask_variable: Any = None

    @staticmethod
    def for_communication_protocol(
        protocol: CommunicationProtocol,
        init_values: List[T] | None = None,
    ) -> ParallelList[T]:
        values: List[T] = init_values or []
        match protocol:
            case CommunicationProtocol.TCP_SOCKET:
                return ParallelList(
                    _parallel_lock=ParallelLock.for_protocol(protocol),
                    _thread_list=values,
                    _concurrency_type=ConcurrencyType.THREAD,
                )
            case CommunicationProtocol.DASK:
                dask_variable = Variable(name=f"parallel_list_{uuid.uuid4()}")
                try:
                    # for the unlikely case that the variable is already initialized, check if it can be got
                    with silenced_logger("distributed.core"):
                        dask_variable.get(timeout=0.3)
                except Exception:
                    # if it does not exist, initialize it
                    dask_variable.set(values)

                return ParallelList(
                    _parallel_lock=ParallelLock.for_protocol(protocol),
                    _concurrency_type=ConcurrencyType.DASK,
                    _dask_variable=dask_variable,
                )
            case _:
                assert_never(protocol)

    def append(self, item: T) -> None:
        with self._parallel_lock:
            match self._concurrency_type:
                case ConcurrencyType.THREAD:
                    self._thread_list.append(item)
                case ConcurrencyType.DASK:
                    current: List[T] = self._get_dask_list()
                    current.append(item)
                    self._dask_variable.set(current)
                case _:
                    assert_never(self._concurrency_type)

    def _get_dask_list(self) -> List[T]:
        return list(self._dask_variable.get())

    def remove(self, item: T) -> None:
        with self._parallel_lock:
            match self._concurrency_type:
                case ConcurrencyType.THREAD:
                    self._thread_list.remove(item)
                case ConcurrencyType.DASK:
                    current: List[T] = self._get_dask_list()
                    current.remove(item)
                    self._dask_variable.set(current)
                case _:
                    assert_never(self._concurrency_type)

    def snapshot(self) -> List[T]:
        with self._parallel_lock:
            match self._concurrency_type:
                case ConcurrencyType.THREAD:
                    return list(self._thread_list)
                case ConcurrencyType.DASK:
                    return list(self._get_dask_list())
                case _:
                    assert_never(self._concurrency_type)

    @contextmanager
    def transaction(self) -> Iterator[ParallelListTransaction[T]]:
        with self._parallel_lock:
            match self._concurrency_type:
                case ConcurrencyType.THREAD:
                    working: List[T] = list(self._thread_list)
                case ConcurrencyType.DASK:
                    working = list(self._get_dask_list())
                case _:
                    assert_never(self._concurrency_type)

            yield ParallelListTransaction(working)

            match self._concurrency_type:
                case ConcurrencyType.THREAD:
                    self._thread_list[:] = working
                case ConcurrencyType.DASK:
                    self._dask_variable.set(working)
                case _:
                    assert_never(self._concurrency_type)

    def __len__(self) -> int:
        return len(self.snapshot())

    def __iter__(self) -> Iterator[T]:
        return iter(self.snapshot())


class ParallelListTransaction[T]:
    def __init__(self, working: List[T]) -> None:
        self._working = working

    def append(self, item: T) -> None:
        self._working.append(item)

    add = append  # alias

    def remove(self, item: T) -> None:
        self._working.remove(item)

    def snapshot(self) -> List[T]:
        return list(self._working)

    def __len__(self) -> int:
        return len(self._working)

    def __iter__(self) -> Iterator[T]:
        return iter(self._working)
