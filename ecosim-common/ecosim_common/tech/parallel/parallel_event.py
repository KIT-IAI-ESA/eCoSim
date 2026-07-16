from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import assert_never

import dask.distributed
from ecosim_common.communication.communication_protocol import CommunicationProtocol


@dataclass
class ParallelEvent:
    """Uniform wrapper over threading.Event and dask.distributed.Event."""

    _event: dask.distributed.Event | threading.Event = field()

    @staticmethod
    def for_communication_protocol(
        communication_protocol: CommunicationProtocol,
    ) -> ParallelEvent:
        match communication_protocol:
            case CommunicationProtocol.DASK:
                return ParallelEvent.dask()
            case CommunicationProtocol.TCP_SOCKET:
                return ParallelEvent.thread()
            case _:
                assert_never(communication_protocol)

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
