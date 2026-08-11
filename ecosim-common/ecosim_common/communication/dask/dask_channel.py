from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from time import sleep
from typing import Callable, override

import dask.distributed as distributed
from ecosim_common.communication.binary_message.binary_message import BinaryMessage, BinaryMessageHeader
from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.binary_message.simple_binary_message import SimpleBinaryMessage
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ChannelHandler, ConnectionData, ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


def create_internal_dask_id() -> str:
    internal_dask_id = uuid.uuid4().hex
    return internal_dask_id


@dataclass
class DaskChannel(ESPChannel, ShutdownListener):
    _logger = ESPLogger("DaskChannel")

    _connection_address: ConnectionAddress = field()
    _is_finished: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _is_listening: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _server_listening: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask(dask_name="server_listen"))
    _closed: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask(dask_name="closed"))
    _connected: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _server_closed: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask(dask_name="server_closed"))
    _internal_dask_id: str = field(default_factory=create_internal_dask_id)
    _internal_dask_client: distributed.Client = field(default_factory=distributed.get_client)
    _origin_id: int = field(default_factory=lambda: uuid.uuid4().int & (1 << 64) - 1)

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    @override
    def close(self) -> None:
        self._is_finished.set()
        connection_address = self._connection_address
        DaskChannel._logger.debug(f"Closing connections to Dask client {connection_address}...")
        if not self._is_internal_dask_client_running():
            DaskChannel._logger.warning(f"Dask client is not running: {self._connection_address}. So nothing is done")
            return
        if not self._server_listening.is_set():
            DaskChannel._logger.debug(f"Server is not listening: {self._connection_address}. So nothing is done")
            return
        # TODO_AFTER_MERGE: find a better place for the dask shutdown routine
        #       also, there is currently a (very unlikely) race condition between setting '_server_listening' in 'listen_async' and the method
        #       'close', that checks for _server_listening.is_set()
        self._server_listening.clear()
        self._server_closed.set()
        if self._is_internal_dask_client_running():
            current_key: str = ""
            try:
                for key in self._internal_dask_client.datasets.keys():
                    current_key = key
                    self._internal_dask_client.unpublish_dataset(key)
            except KeyError as e:
                DaskChannel._logger.error(f"Something went wrong unpublishing key '{current_key}': {e}")
            except Exception as e:
                DaskChannel._logger.error(f"Something went wrong with closing connection on {self._connection_address}: {e}")
        DaskChannel._logger.info(f"Connection to Dask client {connection_address} closed.")

    def _is_internal_dask_client_running(self) -> bool:
        return self._internal_dask_client.status == "running"

    @override
    def listen_on_message_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        dask_client = self._internal_dask_client
        is_finished = self._is_finished
        closed = self._closed
        internal_dask_id = self._internal_dask_id
        origin_id = self._origin_id

        async def listen_start() -> None:
            future = dask_client.submit(
                DaskChannel._listen_async_internal,
                on_message=on_message,
                dask_client=dask_client,
                is_finished_event=is_finished,
                closed=closed,
                dask_id=internal_dask_id,
                origin_id=origin_id,
                pure=False,
            )
            distributed.fire_and_forget(future)

        dask_client.sync(listen_start)

    @override
    def wait_for_finish(
        self,
        timeout_in_seconds: int | None = None,
    ) -> None:
        self._is_finished.wait(timeout_in_seconds)

    @override
    def listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        return self._listen_blocking_internal(
            closed=self._closed,
            is_finished_event=self._is_finished,
            internal_dask_id=self._internal_dask_id,
            origin_id=self._origin_id,
            distributed_client=self._internal_dask_client,
            timeout_in_seconds=timeout_in_seconds,
        )

    @staticmethod
    def _listen_blocking_internal(
        closed: ParallelEvent,
        is_finished_event: ParallelEvent,
        internal_dask_id: str,
        origin_id: int,
        distributed_client: distributed.Client,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        if closed.is_set():
            raise Exception("Dask client has already or is in the process of being disconnected.")
        message: ReceivedBinaryMessage | None = DaskChannel.receive_from_dask_client(
            connection=distributed_client,
            dask_id=internal_dask_id,
            origin_id=origin_id,
        )
        if not message:
            DaskChannel._logger.info("Received empty message -> closing connection")
            is_finished_event.set()
            return None
        return message.to_esp_channel_message()

    @override
    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        # TODO_AFTER_MERGE: newly added 'not self._is_finished.is_set()'
        if not self._connected.is_set() and not self._is_finished.is_set():
            raise Exception("Dask client already closed")
        try:
            data_var = distributed.Queue(name=self._internal_dask_id, client=self._internal_dask_client)
            data_var.put(SimpleBinaryMessage.of_esp_channel_message(message=message), self._origin_id)
        except Exception as e:
            # TODO_AFTER_MERGE: reconnecting is not specified in the abstraction -> either specify or refactor
            DaskChannel._logger.debug(
                f"Send messsage to server failed - recreating dask client connection and try again. Error: {e}",
            )
            # TODO_AFTER_MERGE: this was commented out -> handle this
            # self._internal_dask_client.connect()
            # self._internal_dask_client.send(
            #     SimpleBinaryMessage.of_esp_channel_message(message=message),
            # )

    # Needs to be a static method due to serialization issues when submitting via dd_client.submit().
    # A non-static method would have either the cls or self as the first parameter.
    # In addition, dask.distribute.client.Client.submit expects pure functions by default -> so it makes
    # sense to make it static in any case.
    @staticmethod
    def _listen_async_internal(
        on_message: Callable[[ESPChannelMessage], None],
        dask_client: distributed.Client,
        dask_id: str,
        origin_id: int,
        is_finished_event: ParallelEvent,
        closed: ParallelEvent,
    ) -> None:
        distributed.secede()  # since it is a long-lived task, we need to secede it from the common thread pool to not block other tasks
        while not is_finished_event.is_set():
            message: ESPChannelMessage | None = DaskChannel._listen_blocking_internal(
                closed=closed,
                is_finished_event=is_finished_event,
                internal_dask_id=dask_id,
                origin_id=origin_id,
                distributed_client=dask_client,
                timeout_in_seconds=None,
            )
            if message is not None:
                on_message(message)

    def is_listening_event(self) -> ParallelEvent:
        return self._is_listening

    @override
    def listen_on_connection_loop_async(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        DaskChannel._logger.debug("Starting to listen")
        if self._server_listening.is_set():
            DaskChannel._logger.warning(
                f"Dask client is already listening to: {self._connection_address}. So nothing is done",
            )
            return
        self._server_listening.set()

        async def listen_start() -> None:
            future = self._internal_dask_client.submit(DaskChannel._listen, channel_handler, self._server_closed)
            distributed.fire_and_forget(future)

        self._internal_dask_client.sync(listen_start)

    @override
    def on_app_shutdown(self) -> None:
        self.close()

    @staticmethod
    def _listen(
        on_new_channel: ChannelHandler,
        closed: ParallelEvent,
    ) -> None:
        dask_client = distributed.get_client()
        DaskChannel._logger.debug("Now listening to Dask Client")
        current_connections: list[str] = []
        while not closed.is_set():
            if dask_client.status != "running":
                DaskChannel._logger.error("Cannot listen to Dask client")
                raise Exception
            if len(dask_client.datasets) == len(current_connections):
                # TODO_OSR: find alternative to sleep
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
                        channel=DaskChannel(
                            _connection_address=client_address,
                            _internal_dask_id=dask_id,
                        ),
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
        DaskChannel._logger.debug(f"closed.is_set: {closed.is_set()}")
        DaskChannel._logger.debug(f"Stopped listening to Dask Client on {client_address}")

    @staticmethod
    def receive_from_dask_client(
        connection: distributed.Client,
        dask_id: str,
        origin_id: int,
    ) -> ReceivedBinaryMessage | None:
        while True:
            received_id = None
            DaskChannel._logger.debug(f"Trying to receive for dask_id {dask_id} and origin_id {origin_id}...")
            try:
                data_var = distributed.Queue(name=dask_id, client=connection)
                raw_message = data_var.get(timeout=300)
            except TimeoutError:
                DaskChannel._logger.debug(f"Received no data at {origin_id} after 300 seconds.")
                return None
            except Exception as e:
                DaskChannel._logger.error(f"Received error non-timeout error while waiting at origin_id {origin_id}: {e}")
                raise e
            DaskChannel._logger.debug(f"Trying to receive for dask_id {dask_id} and origin_id {origin_id}...done.")
            try:
                raw_message, received_id = raw_message
            except (ValueError, TypeError):
                pass
            if not raw_message or received_id == origin_id:
                data_var.put((raw_message, received_id))
                continue
            if raw_message == "empty" or dask_id not in connection.datasets.keys():
                DaskChannel._logger.debug(f"Received no data at {origin_id}")
                return None
            raw_header = raw_message[0 : BinaryMessage.HEADER_BYTES]
            message_header = BinaryMessageHeader(raw_header)
            if not message_header:
                DaskChannel._logger.debug("Received no valid header")
                return None
            data: bytes = raw_message[BinaryMessage.HEADER_BYTES :]
            DaskChannel._logger.debug(f"Received message of type {message_header.message_type} at {origin_id} from {received_id}")
            return ReceivedBinaryMessage(message_header, data, ConnectionAddress.of_dask_client(connection))

    def connect(
        self,
    ) -> None:
        dask_client = distributed.get_client()
        distributed.Queue(name=self._internal_dask_id, client=dask_client)
        dask_client.datasets[self._internal_dask_id] = None
        self._connected.set()


# module level, not a method -> pickles by qualname without dragging the endpoint
def _serve_channel_seceded(handler: ChannelHandler, connection_data: ConnectionData) -> None:
    from distributed import secede

    secede()
    handler(connection_data)
