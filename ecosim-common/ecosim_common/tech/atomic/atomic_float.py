import threading


class AtomicFloat:
    def __init__(self,
                 value: float = 0.0
                 ):
        self._value = value
        self._lock = threading.Lock()

    def inc(self,
            d: float,
            ) -> float:
        with self._lock:
            self._value += d
            return self._value

    def dec(self,
            d: float
            ) -> float:
        with self._lock:
            self._value -= d
            return self._value

    @property
    def value(self) -> float:
        with self._lock:
            return self._value
