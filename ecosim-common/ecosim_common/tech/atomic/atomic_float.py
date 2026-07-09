import threading
from dataclasses import dataclass, field
from typing import final

import dask.distributed as dd
from ecosim_common.tech.parallel.parallel_lock import ParallelLock


@final
@dataclass
class AtomicFloatNew:
    _value: float = field()
    _lock: ParallelLock = field()

    @classmethod
    def thread(cls, init_value: float) -> AtomicFloatNew:
        return cls(
            _value=init_value,
            _lock=ParallelLock.thread(),
        )

    @classmethod
    def dask(cls, init_value: float) -> AtomicFloatNew:
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


class AtomicFloat:
    def __init__(
        self,
        value: float = 0.0,
    ):
        self._value = value
        self._lock = threading.Lock()

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


# TODO_AFTER_MERGE: common abstraction between both atomic floats
class AtomicFloatDask:
    def __init__(
        self,
        value: float = 0.0,
    ):
        self._value = value
        self._lock = dd.Lock()

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
