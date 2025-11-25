import dask.distributed as dd
from dataclasses import dataclass, field
from typing import override, Callable

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_endpoint import ESPChannelEndpoint, ConnectionData
from ecosim_common.communication.dask.esp_dask import create_internal_dask_client, ESPDask, is_raw_dask_client_connected
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


def _listen(
        on_new_channel: Callable[[ConnectionData], None],
        _closed: dd.Event,
) -> None:

    dask_client = dd.get_client()
    EndpointDask._logger.debug("Now listening to Dask Client")
    closed = dd.Variable("closed")
    is_closed = closed.get()
    count = 0
    while not is_closed.is_set():

        if dask_client.status != 'running':
            EndpointDask._logger.error("Cannot listen to Dask client")
            raise Exception

        client_address = ConnectionAddress.of_dask_client(dask_client)
        on_new_channel(
            ConnectionData(
                channel=DaskChannel(ESPDask()),
                client_address=client_address,
            ),
        )
        count += 1
        closed = dd.Variable("closed")
        is_closed = closed.get()
    EndpointDask._logger.debug(f"Stopped listening to Dask Client on {client_address}")


@dataclass(frozen=True)
class EndpointDask(ESPChannelEndpoint, ShutdownListener):
    _logger = ESPLogger("EndpointDask")

    _connection_address: ConnectionAddress = field()
    _closed: dd.Event = field(default_factory=dd.Event)
    _listening: dd.Event = field(default_factory=dd.Event)
    _internal_dask_client: dd.Client = field(default_factory=create_internal_dask_client)

    def __post_init__(self):
        ShutdownManager().register_listener(self)

    @override
    def listen_async(
        self,
        on_new_channel: Callable[[ConnectionData], None],
    ) -> None:
        EndpointDask._logger.debug("Starting to listen")
        if self._listening.is_set():
            EndpointDask._logger.warning(
                f"Dask client is already listening to: {self._connection_address}. So nothing is done",
            )
            return

        self._listening.set()

        async def listen_start():
            future = self._internal_dask_client.submit(_listen, on_new_channel, self._closed)
            dd.fire_and_forget(future)

        self._internal_dask_client.sync(listen_start)
        closed_event = dd.Event()
        closed = dd.Variable("closed")
        closed.set(closed_event)

    @override
    def close(self) -> None:
        if self._listening.is_set():
            self._listening.clear()
            self._closed.set()
            closed = dd.Variable("closed")
            closed.set(self._closed)
            if is_raw_dask_client_connected(self._internal_dask_client):
                try:
                    # self._internal_dask_client.shutdown()
                    self._internal_dask_client.scheduler.status  # close()
                    # self._future.cancel()
                except Exception as e:
                    EndpointDask._logger.error(f"Something went wrong with closing connection on {self._connection_address}: {e}")

    def on_app_shutdown(self) -> None:
        self.close()
