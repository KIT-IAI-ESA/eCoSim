from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar, assert_never, final

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_lock import ParallelLock

T = TypeVar("T", int, float)


@final
@dataclass
class Atomic(Generic[T]):
    """
    Thread-safe atomic wrapper for numbers.
    """

    _lock: ParallelLock = field()
    _value: T = field(default=0)

    @classmethod
    def for_protocol(cls, protocol: CommunicationProtocol, init_value: T) -> Atomic[T]:
        match protocol:
            case CommunicationProtocol.DASK:
                return cls.dask(init_value)
            case CommunicationProtocol.TCP_SOCKET:
                return cls.thread(init_value)
            case _:
                assert_never(protocol)

    @classmethod
    def thread(cls, init_value: T) -> Atomic[T]:
        return cls(
            _lock=ParallelLock.thread(),
            _value=init_value,
        )

    @classmethod
    def dask(cls, init_value: T) -> Atomic[T]:
        return cls(
            _lock=ParallelLock.dask(),
            _value=init_value,
        )

    def increment(self, difference: T = 1) -> T:
        """
        Increments the current value and returns the new value. The difference can be negative, then it will be subtracted.

        Args:
            difference: the value to increment by

        Returns:
            The incremented value
        """
        with self._lock:
            self._value = self._value + difference
            return self._value

    def decrement(self, difference: T = 1) -> T:
        """
        Decrements the current value and returns the new value. The difference can be negative, then it will be added.

        Args:
            difference: the value to decrement by

        Returns:
            The decremented value
        """
        with self._lock:
            self._value = self._value - difference
            return self._value

    def set(self, value: T) -> None:
        """
        Sets to the new value.

        Args:
            value: The new value.
        """
        with self._lock:
            self._value = value

    @property
    def value(self) -> T:
        """
        Returns:
            The current value.
        """
        with self._lock:
            return self._value
