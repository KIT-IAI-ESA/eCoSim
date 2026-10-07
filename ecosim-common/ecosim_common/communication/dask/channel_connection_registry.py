from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import ClassVar

import dask.distributed as distributed

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ChannelHandler, ConnectionData
from ecosim_common.communication.dask.channel_endpoint import ChannelEndpoint
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


@dataclass
class ChannelConnectionRegistry(ShutdownListener):
    _logger: ClassVar[ESPLogger] = ESPLogger("ChannelConnectionRegistry")
    _accept_timeout_in_seconds: ClassVar[int] = 30
    _closed_sentinel: ClassVar[str] = "__closed__"

    _connection_queue: ESPQueue[str] = field()
    _dask_client: distributed.Client = field()
    _listening_on_connection: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask(dask_name="ecosim_dask_channel_connection_queue"))
    _start_listening_lock: ParallelLock = field(default_factory=lambda: ParallelLock.dask("ecosim_dask_channel_connection_start_listening_lock"))

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    @staticmethod
    def of(dask_client: distributed.Client) -> ChannelConnectionRegistry:
        return ChannelConnectionRegistry(
            _connection_queue=ESPQueue.of_type(
                queue_type=ESPStructureType.DASK_VARIABLE,
                dask_name="ecosim_dask_channel_connection_queue",
                dask_client=dask_client,
            ),
            _dask_client=dask_client,
        )

    def start_listening(
        self,
        channel_handler: ChannelHandler,
    ) -> bool:
        """Starts the one accept loop of the cluster. Returns False if one is already running."""
        with self._start_listening_lock:
            if self._listening_on_connection.is_set():
                ChannelConnectionRegistry._logger.warning(
                    "There should only be one listener for new dask connection -> this call is skipped but must be investigated.",
                )
                return False
            ChannelConnectionRegistry._logger.debug("Starting to listen on dask connections.")
            self._listening_on_connection.set()

        dask_client = self._dask_client

        async def listen_start() -> None:
            future = dask_client.submit(
                ChannelConnectionRegistry._listen_on_connection_internal,
                channel_handler,
                self._connection_queue,
                self._listening_on_connection,
            )
            distributed.fire_and_forget(future)

        dask_client.sync(listen_start)
        return True

    def stop_listening(self) -> None:
        if self._dask_client.status != "running":
            self._logger.debug("close: dask client is not running -> nothing is done")
            return
        if not self._listening_on_connection.is_set():
            self._logger.debug("stop_listening: not listening on connection -> nothing is done")
            return
        self._listening_on_connection.clear()
        self._connection_queue.push(self._closed_sentinel)

    def close(self) -> None:
        self.stop_listening()

    def on_app_shutdown(self) -> None:
        self.close()

    @staticmethod
    def _listen_on_connection_internal(
        on_new_channel: ChannelHandler,
        connection_queue: ESPQueue[str],
        listening_on_connection: ParallelEvent,
    ) -> None:
        dask_client = distributed.get_client()
        client_address = ConnectionAddress.of_dask_client(dask_client)
        ChannelConnectionRegistry._logger.debug("Now listening to Dask Client")
        try:
            # ATTENTION: only the sentinel ends the loop, never the event. 'stop_listening' clears the event
            # *and* queues the sentinel - a loop leaving on the event would leave the sentinel behind, and
            # that ends the next listener the moment it starts.
            while (
                dask_id := ChannelConnectionRegistry._next_connection_id(dask_client, connection_queue)
            ) != ChannelConnectionRegistry._closed_sentinel:
                if dask_id is not None:
                    ChannelConnectionRegistry._accept_connection(on_new_channel, dask_client, client_address, dask_id)
        except BaseException:
            # nobody accepts any more, so a new listener must be allowed to start
            listening_on_connection.clear()
            raise
        ChannelConnectionRegistry._logger.debug(
            "Stopped listening to Dask Client on %s. (listening_on_connection.is_set(): %s)",
            client_address,
            listening_on_connection.is_set(),
        )

    @staticmethod
    def _next_connection_id(
        dask_client: distributed.Client,
        connection_queue: ESPQueue[str],
    ) -> str | None:
        if dask_client.status != "running":
            ChannelConnectionRegistry._logger.error("Cannot listen to Dask client - dask client is not running.")
            raise ConnectionError("dask client is not running")
        # blocks on the scheduler, so an idle server costs one round trip per timeout and a connecting
        # client is served the moment it announces itself
        return connection_queue.pop_or_none(timeout=ChannelConnectionRegistry._accept_timeout_in_seconds)

    @staticmethod
    def _accept_connection(
        on_new_channel: ChannelHandler,
        dask_client: distributed.Client,
        client_address: ConnectionAddress,
        dask_id: str,
    ) -> None:
        from ecosim_common.communication.dask.dask_channel import DaskChannel

        connection_data = ConnectionData(
            channel=DaskChannel(
                _connection_address=client_address,
                _internal_dask_id=dask_id,
                _connected=ParallelEvent.dask(init_set=True),
                # this is the end that accepted the connection, so it reads the listener inbox
                _endpoint=ChannelEndpoint.LISTENER,
            ),
            client_address=client_address,
        )

        async def submit() -> None:
            future = dask_client.submit(
                ChannelConnectionRegistry._serve_channel_seceded,
                on_new_channel,
                connection_data,
                key=uuid.uuid4().hex,
                pure=False,
            )
            distributed.fire_and_forget(future)

        ChannelConnectionRegistry._logger.debug("Accepted connection, running ChannelHandler.")
        dask_client.sync(submit)

    def register(self, dask_id: str) -> None:
        self._connection_queue.push(dask_id)

    def is_listening_event(self) -> ParallelEvent:
        return self._listening_on_connection

    @staticmethod
    def _serve_channel_seceded(handler: ChannelHandler, connection_data: ConnectionData) -> None:
        from distributed import secede

        secede()
        handler(connection_data)
