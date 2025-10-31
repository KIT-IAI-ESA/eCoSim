import threading


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

    @property
    def value(self) -> int:
        with self._lock:
            return self._value
