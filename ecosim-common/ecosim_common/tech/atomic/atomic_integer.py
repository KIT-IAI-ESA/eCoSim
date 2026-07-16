from __future__ import annotations

from dataclasses import dataclass, field
from typing import assert_never, final

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_lock import ParallelLock


@final
@dataclass
class AtomicInteger:
    _lock: ParallelLock = field()
    _value: int = field(default=0)

    @classmethod
    def for_protocol(
        cls,
        communication_protocol: CommunicationProtocol,
        init_value: int,
    ) -> AtomicInteger:
        lock: ParallelLock
        match communication_protocol:
            case CommunicationProtocol.DASK:
                lock = ParallelLock.dask()
            case CommunicationProtocol.TCP_SOCKET:
                lock = ParallelLock.thread()
            case _:
                assert_never(communication_protocol)

        return cls(
            _lock=lock,
            _value=init_value,
        )

    @classmethod
    def thread(cls, init_value: int) -> AtomicInteger:
        return cls(
            _lock=ParallelLock.thread(),
            _value=init_value,
        )

    @classmethod
    def dask(cls, init_value: int) -> AtomicInteger:
        return cls(
            _lock=ParallelLock.dask(),
            _value=init_value,
        )

    def inc(
        self,
        d: int = 1,
    ) -> int:
        with self._lock:
            self._value += d
            return self._value

    def dec(
        self,
        d: int = 1,
    ) -> int:
        with self._lock:
            self._value -= d
            return self._value

    def set(
        self,
        d: int,
    ) -> int:
        with self._lock:
            self._value = d
            return self._value

    @property
    def value(self) -> int:
        with self._lock:
            return self._value
