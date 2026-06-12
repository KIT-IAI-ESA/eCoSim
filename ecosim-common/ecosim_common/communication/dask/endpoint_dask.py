import dask.distributed as dd
from dataclasses import dataclass, field
from typing import override, Callable

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_endpoint import ESPChannelEndpoint, ConnectionData
from ecosim_common.communication.dask.esp_dask import create_internal_dask_id, ESPDask
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


def _listen(
        on_new_channel: Callable[[ConnectionData], None],
        _closed: dd.Event,
) -> None:

    dask_client = dd.get_client()
    EndpointDask._logger.debug("Now listening to Dask Client")
    closed = dd.Event(name="server_closed")
    global_finish = dd.Event(name="global_finish")
    current_connections: list[str] = []  # dd.publish.Datasets | dict[Any, Any] = {}  # dask_client.datasets
    while not closed.is_set() and not global_finish.is_set():
        # closed = dd.Variable("closed")
        # is_closed = closed.get()
        if dask_client.status != 'running':
            EndpointDask._logger.error("Cannot listen to Dask client")
            raise Exception
        if len(dask_client.datasets) == len(current_connections):
            continue
        elif len(dask_client.datasets) < len(current_connections):
            if closed.is_set():
                return
            raise Exception("Server listening ended sooner than anticipated.")
        else:
            for dask_id in dask_client.datasets.keys():
                if dask_id in current_connections:  # .keys():
                    continue

                client_address = ConnectionAddress.of_dask_client(dask_client)
                on_new_channel(
                ConnectionData(
                        channel=DaskChannel(ESPDask(dask_id)),
                        client_address=client_address,
                ),
                )
                current_connections.append(dask_id)
    EndpointDask._logger.debug(f"Stopped listening to Dask Client on {client_address}")


@dataclass(frozen=True)
class EndpointDask(ESPChannelEndpoint, ShutdownListener):
    _logger = ESPLogger("EndpointDask")

    _connection_address: ConnectionAddress = field()
    _closed: dd.Event = field(default_factory=dd.Event)
    _listening: dd.Event = field(default_factory=dd.Event)
    _internal_dask_id: str = field(default_factory=create_internal_dask_id)
    _internal_dask_client: dd.Client = field(default_factory=dd.get_client)

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)
        self._closed.name = "server_closed"
        self._listening.name = "server_listen"
        # Ensure Events are cleared. Mostly for testing purposes
        self._closed.clear()
        self._listening.clear()

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

        async def listen_start() -> None:
            future = self._internal_dask_client.submit(_listen, on_new_channel, self._closed)
            dd.fire_and_forget(future)

        self._internal_dask_client.sync(listen_start)
        # closed_event = dd.Event()
        # closed = dd.Variable("closed")
        # closed.set(closed_event)

    @override
    def close(self) -> None:
        if self._listening.is_set():
            self._listening.clear()
            self._closed.set()
            # closed = dd.Variable("closed")
            # closed.set(self._closed)
            # channel_close = dd.Variable("finished_channel")
            # channel_close.set(self._closed)
            if self._internal_dask_client.status == "running":
                try:
                    for key in self._internal_dask_client.datasets.keys():
                        self._internal_dask_client.unpublish_dataset(key)
                except KeyError:
                    print(self._internal_dask_client.datasets.keys())

                except Exception as e:
                    EndpointDask._logger.error(f"Something went wrong with closing connection on {self._connection_address}: {e}")

    def on_app_shutdown(self) -> None:
        self.close()
