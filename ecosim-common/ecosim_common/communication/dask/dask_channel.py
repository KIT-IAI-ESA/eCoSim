from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from time import sleep
from typing import Any, Callable, override

import dask.distributed as distributed
from ecosim_common.communication.binary_message import binary_message_header
from ecosim_common.communication.binary_message.binary_message_header import BinaryMessageHeader
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
    # queued by 'close()' in place of a message to tell the peer that this side hung up
    _CLOSED_SENTINEL = "__closed__"

    _connection_address: ConnectionAddress = field()
    _is_finished: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _is_listening: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _listening_on_connection: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _closed: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _connected: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _internal_dask_id: str = field(default_factory=create_internal_dask_id)
    # resolved lazily via '_dask_client()' - never eagerly, so that a channel can be unpickled on a
    # worker before that worker is able to hand out a client
    _internal_dask_client: distributed.Client | None = field(default=None)
    _origin_id: int = field(default_factory=lambda: uuid.uuid4().int & (1 << 64) - 1)

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    def _dask_client(self) -> distributed.Client:
        if self._internal_dask_client is None:
            self._internal_dask_client = distributed.get_client()
        return self._internal_dask_client

    def __getstate__(self) -> dict[str, Any]:
        # 'distributed.Client' holds live asyncio objects (tasks, futures, comms) and is therefore not
        # picklable at all. The channel travels without it; the receiving side resolves its own local
        # client on first use. Everything else on the channel is either plain data or a dask primitive
        # with a '__reduce__' (see 'ParallelEventDask'), so it survives the trip.
        return {**self.__dict__, "_internal_dask_client": None}

    @override
    def close(self) -> None:
        self._is_finished.set()
        DaskChannel._logger.debug("Closing connections to Dask client %s...", self._connection_address)
        if not self._is_internal_dask_client_running():
            DaskChannel._logger.warning("Dask client is not running: %s. So nothing is done", self._connection_address)
            return
        if not self._listening_on_connection.is_set() and not self._connected.is_set():
            DaskChannel._logger.debug("Server is not listening: %s. So nothing is done", self._connection_address)
            return
        # TODO_AFTER_MERGE: find a better place for the dask shutdown routine
        #       also, there is currently a (very unlikely) race condition between setting '_server_listening' in 'listen_async' and the method
        #       'close', that checks for _server_listening.is_set()
        if self._listening_on_connection.is_set():
            # only the channel that accepts connections owns an accept loop that has to be stopped -
            self._listening_on_connection.clear()
        # Only unpublish own connection marker. Every other key on this dask client
        # belongs to a different channel, and dropping it makes that channel's reader see
        # 'dask_id not in datasets' - i.e. it reads the removal as its peer hanging up.
        try:
            if self._internal_dask_id in self._dask_client().datasets.keys():
                self._dask_client().unpublish_dataset(self._internal_dask_id)
        except KeyError as e:
            DaskChannel._logger.error("Something went wrong unpublishing key '%s': %s", self._internal_dask_id, e)
        except Exception as e:
            DaskChannel._logger.error("Something went wrong with closing connection on %s: %s", self._connection_address, e)
        self._signal_close_to_peer()
        DaskChannel._logger.info("Connection to Dask client %s closed.", self._connection_address)

    def _signal_close_to_peer(self) -> None:
        try:
            data_var = distributed.Queue(name=self._internal_dask_id, client=self._dask_client())
            data_var.put((DaskChannel._CLOSED_SENTINEL, self._origin_id))
        except Exception as e:
            DaskChannel._logger.debug("Could not signal close on %s: %s", self._connection_address, e)

    def _is_internal_dask_client_running(self) -> bool:
        try:
            return self._dask_client().status == "running"
        except ValueError:
            return False

    @override
    def listen_on_message_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        dask_client = self._dask_client()
        is_finished = self._is_finished
        closed = self._closed
        internal_dask_id = self._internal_dask_id
        origin_id = self._origin_id

        async def listen_start() -> None:
            future = dask_client.submit(
                DaskChannel._listen_async_internal,
                on_message=on_message,
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
            distributed_client=self._dask_client(),
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
            data_var = distributed.Queue(name=self._internal_dask_id, client=self._dask_client())
            # both endpoints share this one queue, so every entry carries its sender - see
            # 'receive_from_dask_client', which puts entries of its own origin back
            data_var.put(
                (
                    SimpleBinaryMessage.of_esp_channel_message(message=message).raw_message(),
                    self._origin_id,
                ),
            )
        except Exception as e:
            # TODO_AFTER_MERGE: reconnecting is not specified in the abstraction -> either specify or refactor
            DaskChannel._logger.debug("Send messsage to server failed - recreating dask client connection and try again. Error: %s", e)
            # TODO_AFTER_MERGE: this was commented out -> handle this
            # self._internal_dask_client.connect()
            # self._internal_dask_client.send(
            #     SimpleBinaryMessage.of_esp_channel_message(message=message),
            # )

    # Needs to be a static method due to serialization issues when submitting via distributed_client.submit().
    # A non-static method would have either the cls or self as the first parameter.
    # In addition, dask.distribute.client.Client.submit expects pure functions by default -> so it makes
    # sense to make it static in any case.
    @staticmethod
    def _listen_async_internal(
        on_message: Callable[[ESPChannelMessage], None],
        dask_id: str,
        origin_id: int,
        is_finished_event: ParallelEvent,
        closed: ParallelEvent,
    ) -> None:
        distributed.secede()  # since it is a long-lived task, we need to secede it from the common thread pool to not block other tasks
        dask_client = distributed.get_client()
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
        if self._listening_on_connection.is_set():
            DaskChannel._logger.warning("Dask client is already listening to: %s. So nothing is done", self._connection_address)
            return
        self._listening_on_connection.set()

        dask_client = self._dask_client()

        async def listen_start() -> None:
            future = dask_client.submit(DaskChannel._listen_on_connection_internal, channel_handler, self._listening_on_connection)
            distributed.fire_and_forget(future)

        dask_client.sync(listen_start)

    @override
    def on_app_shutdown(self) -> None:
        self.close()

    @staticmethod
    def _listen_on_connection_internal(
        on_new_channel: ChannelHandler,
        listening_on_connection: ParallelEvent,
    ) -> None:
        dask_client = distributed.get_client()
        client_address = ConnectionAddress.of_dask_client(dask_client)
        DaskChannel._logger.debug("Now listening to Dask Client")
        current_connections: list[str] = []
        while listening_on_connection.is_set():
            if dask_client.status != "running":
                DaskChannel._logger.error("Cannot listen to Dask client")
                raise Exception
            if len(dask_client.datasets) == len(current_connections):
                # TODO_OSR: find alternative to sleep
                sleep(3)  # if all clients are connected, we need to free the loop from the massive event checks
                continue
            elif len(dask_client.datasets) < len(current_connections):
                if not listening_on_connection.is_set():
                    return
                raise Exception("Server listening ended sooner than anticipated.")
            else:
                for dask_id in dask_client.datasets.keys():
                    if dask_id in current_connections:
                        continue

                    connection_data = ConnectionData(
                        channel=DaskChannel(
                            _connection_address=client_address,
                            _internal_dask_id=dask_id,
                            _connected=ParallelEvent.dask(init_set=True),
                        ),
                        client_address=client_address,
                    )

                    # bound as defaults so the closure cannot pick up the next loop iteration's values
                    async def submit(connection_data: ConnectionData = connection_data) -> None:
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
        DaskChannel._logger.debug(
            "Stopped listening to Dask Client on %s. (listening_on_connection.is_set(): %s)",
            client_address,
            listening_on_connection.is_set(),
        )

    @staticmethod
    def receive_from_dask_client(
        connection: distributed.Client,
        dask_id: str,
        origin_id: int,
    ) -> ReceivedBinaryMessage | None:
        while True:
            DaskChannel._logger.debug("Trying to receive for dask_id %s and origin_id %s...", dask_id, origin_id)
            try:
                data_var = distributed.Queue(name=dask_id, client=connection)
                queue_entry = data_var.get(timeout=300)
            except TimeoutError:
                DaskChannel._logger.debug("Received no data at %s after 300 seconds.", origin_id)
                return None
            except Exception as e:
                DaskChannel._logger.error("Received error non-timeout error while waiting at origin_id %s: %s", origin_id, e)
                raise e
            DaskChannel._logger.debug("Trying to receive for dask_id %s and origin_id %s...done.", dask_id, origin_id)
            # 'send' always queues a (raw_message, origin_id) pair - see the comment there
            raw_message, received_id = queue_entry
            if raw_message == DaskChannel._CLOSED_SENTINEL:
                # put it back: the sentinel is what every reader on this queue hangs on, and
                # consuming it here would leave the others parked until their 300s timeout
                data_var.put(queue_entry)
                DaskChannel._logger.debug("Received close signal at %s", origin_id)
                return None
            if received_id == origin_id:
                data_var.put(queue_entry)  # our own message -> hand it back to the peer
                # without this the loop re-reads its own message thousands of times per second
                sleep(0.01)
                continue
            if not raw_message or dask_id not in connection.datasets.keys():
                DaskChannel._logger.debug("Received no data at %s", origin_id)
                return None
            raw_header = raw_message[0 : binary_message_header.HEADER_BYTES]
            message_header = BinaryMessageHeader(raw_header)
            if not message_header:
                DaskChannel._logger.debug("Received no valid header")
                return None
            data: bytes = raw_message[binary_message_header.HEADER_BYTES :]
            DaskChannel._logger.debug("Received message of type %s at %s from %s", message_header.message_type, origin_id, received_id)
            return ReceivedBinaryMessage(message_header, data, ConnectionAddress.of_dask_client(connection))

    @override
    def connect(
        self,
    ) -> None:
        dask_client = distributed.get_client()
        distributed.Queue(name=self._internal_dask_id, client=dask_client)
        dask_client.datasets[self._internal_dask_id] = None
        self._connected.set()

    @override
    def is_connected(self) -> bool:
        return self._connected.is_set()

    @override
    def is_listening_on_connection_event(self) -> ParallelEvent:
        return self._listening_on_connection


# module level, not a method -> pickles by qualname without dragging the endpoint
def _serve_channel_seceded(handler: ChannelHandler, connection_data: ConnectionData) -> None:
    from distributed import secede

    secede()
    handler(connection_data)
