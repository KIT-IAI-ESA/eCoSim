from __future__ import annotations

import threading
from dataclasses import dataclass, field

import dask.distributed


@dataclass
class ParallelEvent:
    """Uniform wrapper over threading.Event and dask.distributed.Event."""

    _event: dask.distributed.Event | threading.Event = field()

    @staticmethod
    def for_communication_protocol(
        communication_protocol: str,
    ) -> ParallelEvent:
        if communication_protocol == "dask":
            return ParallelEvent.dask()
        elif communication_protocol == "tcp_socket":
            return ParallelEvent.thread()
        else:
            raise ValueError(f"Unknown communication protocol: {communication_protocol}")

    @staticmethod
    def thread() -> ParallelEvent:
        return ParallelEvent(
            _event=threading.Event(),
        )

    @staticmethod
    def dask(
        name: str | None = None,
        client: dask.distributed.Client | None = None,
    ) -> ParallelEvent:
        return ParallelEvent(
            _event=dask.distributed.Event(name=name, client=client),
        )

    def set(self) -> None:
        # actually, the dask implementation returns something
        self._event.set()

    def clear(self) -> None:
        # actually, the dask implementation returns something
        self._event.clear()

    def is_set(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._event.wait(timeout=timeout)
