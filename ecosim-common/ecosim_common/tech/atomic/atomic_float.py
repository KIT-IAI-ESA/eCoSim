from __future__ import annotations

from dataclasses import dataclass, field
from typing import assert_never, final

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_lock import ParallelLock


@final
@dataclass
class AtomicFloat:
    _lock: ParallelLock = field()
    _value: float = field(default=0.0)

    @classmethod
    def for_protocol(
        cls,
        communication_protocol: CommunicationProtocol,
        init_value: float,
    ) -> AtomicFloat:
        lock: ParallelLock
        match communication_protocol:
            case CommunicationProtocol.DASK:
                lock = ParallelLock.dask()
            case CommunicationProtocol.TCP_SOCKET:
                lock = ParallelLock.thread()
            case _:
                assert_never(communication_protocol)

        return cls(
            _value=init_value,
            _lock=lock,
        )

    @classmethod
    def thread(cls, init_value: float) -> AtomicFloat:
        return cls(
            _value=init_value,
            _lock=ParallelLock.thread(),
        )

    @classmethod
    def dask(cls, init_value: float) -> AtomicFloat:
        return cls(
            _value=init_value,
            _lock=ParallelLock.dask(),
        )

    def inc(
        self,
        d: float,
    ) -> float:
        with self._lock:
            self._value += d
            return self._value

    def dec(
        self,
        d: float,
    ) -> float:
        with self._lock:
            self._value -= d
            return self._value

    def set(
        self,
        d: float,
    ) -> float:
        with self._lock:
            self._value = d
            return self._value

    @property
    def value(self) -> float:
        with self._lock:
            return self._value
