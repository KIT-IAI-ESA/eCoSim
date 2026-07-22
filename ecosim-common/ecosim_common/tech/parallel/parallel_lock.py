from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from types import TracebackType
from typing import assert_never, override

import dask.distributed
from ecosim_common.communication.communication_protocol import CommunicationProtocol


@dataclass
class ParallelLock(AbstractContextManager, ABC):
    @staticmethod
    def for_protocol(
        communication_protocol: CommunicationProtocol,
        dask_name: str | None = None,
    ) -> "ParallelLock":
        match communication_protocol:
            case CommunicationProtocol.DASK:
                return ParallelLock.dask(name=dask_name)
            case CommunicationProtocol.TCP_SOCKET:
                return ParallelLock.thread()
            case _:
                assert_never(communication_protocol)

    @staticmethod
    def no_lock() -> "ParallelLock":
        return NullLock()

    @staticmethod
    def thread() -> "ParallelLock":
        return ParallelLockImpl(
            _lock=threading.Lock(),
            _none_timeout=-1,
        )

    @staticmethod
    def dask(name: str | None = None) -> ParallelLock:
        return ParallelLockImpl(
            _lock=dask.distributed.Lock(name=name),
            _none_timeout=None,
        )

    @abstractmethod
    def acquire(
        self,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        pass

    @abstractmethod
    def release(self) -> None:
        pass

    @abstractmethod
    def locked(self) -> bool:
        pass

    @abstractmethod
    def _enter(self) -> ParallelLock:
        pass

    @abstractmethod
    def _exit(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        pass

    @override
    def __enter__(self) -> ParallelLock:
        return self._enter()

    @override
    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        self._exit(exc_type, exc_value, traceback)


@dataclass
class ParallelLockImpl(ParallelLock):
    """Uniform wrapper over threading.Lock and dask.distributed.Lock."""

    _lock: threading.Lock | dask.distributed.Lock = field()
    _none_timeout: float | None = field()

    @override
    def acquire(
        self,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        return self._lock.acquire(
            blocking=blocking,
            timeout=timeout or self._none_timeout,  # type: ignore[arg-type] # due to hard coded 'none' type we always get correct values
        )

    @override
    def release(self) -> None:
        # actually, the dask implementation returns a boolean
        self._lock.release()

    @override
    def locked(self) -> bool:
        return self._lock.locked()

    @override
    def _enter(self) -> ParallelLock:
        self._lock.__enter__()
        return self

    @override
    def _exit(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        self._lock.__exit__(
            exc_type,
            exc_value,
            traceback,
        )


class NullLock(ParallelLock):
    def acquire(self, blocking: bool = True, timeout: float | None = None) -> bool:
        return True

    def release(self) -> None:
        return

    def __enter__(self) -> NullLock:
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        return

    def locked(self) -> bool:
        return False

    @override
    def _enter(self) -> ParallelLock:
        return self

    @override
    def _exit(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        return
