import uuid
from dataclasses import dataclass, field
from time import sleep
from typing import override

import dask.distributed as distributed
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_endpoint import ChannelHandler, ConnectionData, ESPChannelEndpoint
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.communication.dask.esp_dask import ESPDask, create_internal_dask_id
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


@dataclass(frozen=True)
class EndpointDask(ESPChannelEndpoint, ShutdownListener):
    _logger = ESPLogger("EndpointDask")

    _connection_address: ConnectionAddress = field()
    _server_closed: distributed.Event = field(default_factory=lambda: distributed.Event(name="server_closed"))
    _server_listening: distributed.Event = field(default_factory=lambda: distributed.Event(name="server_listen"))
    _internal_dask_id: str = field(default_factory=create_internal_dask_id)
    _internal_dask_client: distributed.Client = field(default_factory=distributed.get_client)

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    @override
    def listen_async(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        EndpointDask._logger.debug("Starting to listen")
        if self._server_listening.is_set():
            EndpointDask._logger.warning(
                f"Dask client is already listening to: {self._connection_address}. So nothing is done",
            )
            return
        self._server_listening.set()

        async def listen_start() -> None:
            future = self._internal_dask_client.submit(EndpointDask._listen, channel_handler, self._server_closed)
            distributed.fire_and_forget(future)

        self._internal_dask_client.sync(listen_start)

    @override
    def close(self) -> None:
        if not self._internal_dask_client.status == "running":
            EndpointDask._logger.warning(f"Dask client is not running: {self._connection_address}. So nothing is done")
            return
        if not self._server_listening.is_set():
            EndpointDask._logger.debug(f"Server is not listening: {self._connection_address}. So nothing is done")
            return
        # TODO_AFTER_MERGE: find a better place for the dask shutdown routine
        #       also, there is currently a (very unlikely) race condition between setting '_server_listening' in 'listen_async' and the method
        #       'close', that checks for _server_listening.is_set()
        self._server_listening.clear()
        self._server_closed.set()
        if self._internal_dask_client.status == "running":
            current_key: str = ""
            try:
                for key in self._internal_dask_client.datasets.keys():
                    current_key = key
                    self._internal_dask_client.unpublish_dataset(key)
            except KeyError as e:
                EndpointDask._logger.error(f"Something went wrong unpublishing key '{current_key}': {e}")
            except Exception as e:
                EndpointDask._logger.error(f"Something went wrong with closing connection on {self._connection_address}: {e}")

    def on_app_shutdown(self) -> None:
        self.close()

    @staticmethod
    def _listen(
        on_new_channel: ChannelHandler,
        _closed: distributed.Event,
    ) -> None:
        dask_client = distributed.get_client()
        EndpointDask._logger.debug("Now listening to Dask Client")
        closed = distributed.Event(name="server_closed")
        global_finish = distributed.Event(name="global_finish")
        current_connections: list[str] = []
        while not closed.is_set() and not global_finish.is_set():
            if dask_client.status != "running":
                EndpointDask._logger.error("Cannot listen to Dask client")
                raise Exception
            if len(dask_client.datasets) == len(current_connections):
                sleep(3)  # if all clients are connected, we need to free the loop from the massive event checks
                continue
            elif len(dask_client.datasets) < len(current_connections):
                if closed.is_set():
                    return
                raise Exception("Server listening ended sooner than anticipated.")
            else:
                for dask_id in dask_client.datasets.keys():
                    if dask_id in current_connections:
                        continue

                    client_address = ConnectionAddress.of_dask_client(dask_client)

                    connection_data = ConnectionData(
                        channel=DaskChannel(ESPDask(dask_id)),
                        client_address=client_address,
                    )

                    async def submit() -> None:
                        future = dask_client.submit(
                            _serve_channel_seceded,
                            on_new_channel,
                            connection_data,
                            key=uuid.uuid4().hex,
                            pure=False,
                        )
                        distributed.fire_and_forget(future)

                    dask_client.sync(submit)
                    current_connections.append(dask_id)
        EndpointDask._logger.debug(f"closed.is_set: {closed.is_set()} | global_finish.is_set: {global_finish.is_set()}")
        EndpointDask._logger.debug(f"Stopped listening to Dask Client on {client_address}")


# module level, not a method -> pickles by qualname without dragging the endpoint
def _serve_channel_seceded(handler: ChannelHandler, connection_data: ConnectionData) -> None:
    from distributed import secede

    secede()
    handler(connection_data)
