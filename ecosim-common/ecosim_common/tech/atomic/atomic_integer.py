import threading
import dask.distributed as dd


class AtomicInteger:
    def __init__(
        self,
        value: int = 0,
    ):
        self._value = value
        self._lock = threading.Lock()

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


# TODO_AFTER_MERGE: common abstraction between both atomic integers
class AtomicIntegerDask:
    def __init__(
        self,
        value: int = 0,
    ):
        self._value = value
        self._lock = dd.Lock()

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

    @property
    def value(self) -> int:
        with self._lock:
            return self._value
