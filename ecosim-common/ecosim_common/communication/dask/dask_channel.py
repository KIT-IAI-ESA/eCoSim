from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, cast, override

import dask.distributed as distributed

from ecosim_common.communication.binary_message import binary_message_header
from ecosim_common.communication.binary_message.binary_message_header import BinaryMessageHeader
from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.binary_message.simple_binary_message import SimpleBinaryMessage
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ChannelHandler, ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.dask.channel_connection_registry import ChannelConnectionRegistry
from ecosim_common.communication.dask.channel_endpoint import ChannelEndpoint
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager

# how long a receive without an explicit timeout waits before it treats the connection as dead
_DEFAULT_RECEIVE_TIMEOUT_IN_SECONDS = 300


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
    _closed: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _connected: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())
    _internal_dask_id: str = field(default_factory=create_internal_dask_id)
    # resolved lazily via '_dask_client()' - never eagerly, so that a channel can be unpickled on a
    # worker before that worker is able to hand out a client
    _internal_dask_client: distributed.Client | None = field(default=None)
    # which end of the connection this is - it decides which of the two inboxes is read and which is
    # written. Only the channel created by the accept loop is the listener, everything else connects.
    _endpoint: ChannelEndpoint = field(default=ChannelEndpoint.CONNECTOR)
    # both handles are created on first use and then kept, see '_queue_of'
    _inbox_queue: distributed.Queue | None = field(default=None, init=False, repr=False)
    _peer_inbox_queue: distributed.Queue | None = field(default=None, init=False, repr=False)
    _channel_connection_registry: ChannelConnectionRegistry | None = field(default=None, init=False, repr=False)
    # the accept loop is one per cluster and shared by every channel, so only the channel that started it may stop it
    _started_listening: bool = field(default=False, init=False)

    @staticmethod
    def of(
        connection_address: ConnectionAddress,
        dask_id: str | None = None,
    ) -> DaskChannel:
        return DaskChannel(
            _connection_address=connection_address,
            _internal_dask_id=dask_id or create_internal_dask_id(),
        )

    @override
    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    def _get_or_create_inbox(self) -> distributed.Queue:
        """The queue this endpoint reads."""
        if self._inbox_queue is None:
            self._inbox_queue = self._queue_of(self._endpoint)
        return self._inbox_queue

    def _peer_inbox(self) -> distributed.Queue:
        if self._peer_inbox_queue is None:
            self._peer_inbox_queue = self._queue_of(self._endpoint.peer())
        return self._peer_inbox_queue

    def _queue_of(self, endpoint: ChannelEndpoint) -> distributed.Queue:
        # ATTENTION: 'distributed.Queue.__init__' is a blocking 'queue_create' on the scheduler, so a
        # handle per call costs a round trip on top of every put and get - see 'DaskESPQueue'.
        return distributed.Queue(name=endpoint.inbox_name(self._internal_dask_id), client=self._dask_client())

    def _dask_client(self) -> distributed.Client:
        if self._internal_dask_client is None:
            self._internal_dask_client = distributed.get_client()
        return self._internal_dask_client

    def __getstate__(self) -> dict[str, Any]:
        # 'distributed.Client' holds live asyncio objects (tasks, futures, comms) and is therefore not
        # picklable at all. The channel travels without it; the receiving side resolves its own local
        # client on first use. Everything else on the channel is either plain data or a dask primitive
        # with a '__reduce__' (see 'ParallelEventDask'), so it survives the trip.
        # The queue handles are dropped for the same reason they are cached: 'distributed.Queue.__reduce__'
        # re-runs '__init__', so carrying them would cost a scheduler round trip per unpickling.
        return {**self.__dict__, "_internal_dask_client": None, "_inbox_queue": None, "_peer_inbox_queue": None, "_channel_connection_registry": None}

    @override
    def close(self) -> None:
        self._is_finished.set()
        DaskChannel._logger.debug("Closing connections to Dask client %s...", self._connection_address)
        if not self._is_internal_dask_client_running():
            DaskChannel._logger.warning("Dask client is not running: %s. So nothing is done", self._connection_address)
            return
        if self._started_listening:
            self._channel_registry().stop_listening()
        if self._connected.is_set():
            self._signal_close()
        DaskChannel._logger.info("Connection to Dask client %s closed.", self._connection_address)

    def _signal_close(self) -> None:
        """
        Writes the sentinel into both inboxes.

        The peer's inbox tells the other side that this one hung up. The own inbox wakes this side's
        reader, which is parked in a blocking 'get' and would otherwise sit there until its timeout -
        closing a channel has to end its own receive, exactly like a closed socket returns no data.
        """
        try:
            self._peer_inbox().put(DaskChannel._CLOSED_SENTINEL)
            self._get_or_create_inbox().put(DaskChannel._CLOSED_SENTINEL)
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
        # The handler is deliberately NOT submitted to the cluster. Submitting it would pickle its
        # '__self__', i.e. the whole endpoint that registered it - and an endpoint typically owns
        # process-local resources that cannot be pickled at all (an FMU's ctypes handle, a Matlab
        # engine, a Pyro5 proxy). It would also run the handler on a *copy*, so every mutation it
        # makes would be invisible to the process that started listening.
        # Only the messages cross the wire, through the 'distributed.Queue' that 'send' publishes to.
        if self._is_listening.is_set():
            DaskChannel._logger.warning("Dask channel is already listening to: %s. So nothing is done.", self._connection_address)
            return
        listen_thread = threading.Thread(
            target=self._listen_on_message,
            args=(on_message,),
            name=f"dask-channel-{self._internal_dask_id}",
            # the main thread parks on 'wait_for_finish' for the whole run, so this thread never keeps
            # a finished process alive on its own
            daemon=True,
        )
        listen_thread.start()

    def _listen_on_message(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        self._is_listening.set()
        try:
            while not self._is_finished.is_set():
                message = self.listen_blocking()
                if message is not None:
                    on_message(message)
        finally:
            self._is_listening.clear()

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
        if self._closed.is_set():
            raise Exception("Dask client has already or is in the process of being disconnected.")
        message: ReceivedBinaryMessage | None = self._receive(timeout_in_seconds or _DEFAULT_RECEIVE_TIMEOUT_IN_SECONDS)
        if not message:
            DaskChannel._logger.info("Received empty message -> closing connection")
            self._is_finished.set()
            return None
        return message.to_esp_channel_message()

    @override
    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        if not self._connected.is_set() and not self._is_finished.is_set():
            raise Exception("Dask client already closed")
        try:
            self._peer_inbox().put(SimpleBinaryMessage.of_esp_channel_message(message=message).raw_message())
        except Exception as e:
            DaskChannel._logger.error("Send messsage to server failed. Error: %s", e)

    def is_listening_event(self) -> ParallelEvent:
        return self._is_listening

    @override
    def listen_on_connection_loop_async(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        DaskChannel._logger.debug("Starting to listen")
        self._started_listening = self._channel_registry().start_listening(channel_handler)

    def _channel_registry(self) -> ChannelConnectionRegistry:
        if self._channel_connection_registry is not None:
            return self._channel_connection_registry
        with ParallelLock.dask(name="channel_connection_registry_creation_lock"):
            if self._channel_connection_registry is None:
                self._channel_connection_registry = ChannelConnectionRegistry.of(self._dask_client())
        return self._channel_connection_registry

    @override
    def on_app_shutdown(self) -> None:
        self.close()

    def _receive(
        self,
        timeout_in_seconds: int,
    ) -> ReceivedBinaryMessage | None:
        raw_message = self._next_inbox_entry(timeout_in_seconds)
        if not isinstance(raw_message, bytes) or not raw_message:
            # anything that is not a raw message is '_CLOSED_SENTINEL' or nothing at all
            DaskChannel._logger.debug("Received no data or the close signal on %s", self._inbox_name())
            return None
        message_header = BinaryMessageHeader(raw_message[0 : binary_message_header.HEADER_BYTES])
        if not message_header:
            DaskChannel._logger.debug("Received no valid header on %s", self._inbox_name())
            return None
        data: bytes = raw_message[binary_message_header.HEADER_BYTES :]
        DaskChannel._logger.debug("Received message of type %s on %s", message_header.message_type, self._inbox_name())
        return ReceivedBinaryMessage(message_header, data)

    def _next_inbox_entry(
        self,
        timeout_in_seconds: int,
    ) -> bytes | str | None:
        """Blocks on the scheduler until the peer writes - no polling, so a busy peer costs nothing."""
        try:
            return cast(bytes | str, self._get_or_create_inbox().get(timeout=timeout_in_seconds))
        except TimeoutError:
            DaskChannel._logger.debug("Received no data on %s after %s seconds.", self._inbox_name(), timeout_in_seconds)
            return None
        except Exception as e:
            DaskChannel._logger.error("Received non-timeout error while waiting on %s: %s", self._inbox_name(), e)
            raise e

    def _inbox_name(self) -> str:
        return self._endpoint.inbox_name(self._internal_dask_id)

    @override
    def connect(
        self,
    ) -> None:
        with ParallelLock.dask(name=f"channel_connect_lock_{self._internal_dask_id}"):
            if self._connected.is_set():
                DaskChannel._logger.error("Channel for %s is already connected -> nothing is done.", self._inbox_name())
                return
            dask_client = distributed.get_client()
            self._internal_dask_client = dask_client
            # create the inbox
            self._get_or_create_inbox()
            self._channel_registry().register(self._internal_dask_id)
            self._connected.set()

    @override
    def is_connected(self) -> bool:
        return self._connected.is_set()

    @override
    def is_listening_on_connection_event(self) -> ParallelEvent:
        return self._channel_registry().is_listening_event()
