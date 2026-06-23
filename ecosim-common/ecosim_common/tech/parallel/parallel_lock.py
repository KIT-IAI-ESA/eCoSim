from __future__ import annotations
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
import threading
from types import TracebackType
from typing import override

import dask.distributed


@dataclass
class ParallelLock(AbstractContextManager):
    """Uniform wrapper over threading.Lock and dask.distributed.Lock."""

    _lock: threading.Lock | dask.distributed.Lock = field()
    _none_timeout: float | None = field()

    @staticmethod
    def thread() -> "ParallelLock":
        return ParallelLock(
            _lock=threading.Lock(),
            _none_timeout=-1,
        )

    @staticmethod
    def dask(name: str | None = None, client: dask.distributed.Client | None = None) -> ParallelLock:
        return ParallelLock(
            _lock=dask.distributed.Lock(name=name, client=client),
            _none_timeout=None,
        )

    def acquire(
        self,
        blocking: bool = True,
        timeout: float | None = None,
    ) -> bool:
        return self._lock.acquire(
            blocking=blocking,
            timeout=timeout or self._none_timeout,  # type: ignore[arg-type] # due to hard coded 'none' type we always get correct values
        )

    def release(self) -> None:
        # actually, the dask implementation returns a boolean
        self._lock.release()

    def locked(self) -> bool:
        return self._lock.locked()

    @override
    def __enter__(self) -> ParallelLock:
        self._lock.__enter__()
        return self

    @override
    def __exit__(self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None) -> None:
        self._lock.__exit__(
            exc_type,
            exc_value,
            traceback,
        )
