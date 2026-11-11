from __future__ import annotations

import socket
import threading
from dataclasses import dataclass, field
from typing import Callable, ClassVar, override

from ecosim_common.communication.binary_message import binary_message_header
from ecosim_common.communication.binary_message.binary_message_header import BinaryMessageHeader
from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.binary_message.simple_binary_message import SimpleBinaryMessage
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ChannelHandler, ConnectionData, ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.config.executing_platform import ExecutingPlatform
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager

# not every platform wakes a blocked accept() on close(), so the accept loop checks for it this often
ACCEPT_TIMEOUT_IN_SECONDS = 0.2
# limited, so that a stuck accept thread cannot hold up the shutdown
ACCEPT_LOOP_END_TIMEOUT_IN_SECONDS = 2


@dataclass
class TCPSocket(ESPChannel, ShutdownListener):
    _logger: ClassVar[ESPLogger] = ESPLogger("TCPSocket")

    _internal_socket: socket.socket = field()
    _connection_address: ConnectionAddress = field()
    _closed: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _connected: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _bound: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _listening: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _listening_on_connection: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _start_listening_in_progress: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _accept_loop_ended: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())

    @override
    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    @staticmethod
    def create(connection_address: ConnectionAddress) -> TCPSocket:
        # AF_INET: address family internet => socket is using IPv4
        # SOCK_STREAM: byte-stream communication (by TCP)
        internal_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        TCPSocket._setup_internal_socket(internal_socket)
        return TCPSocket(
            _internal_socket=internal_socket,
            _connection_address=connection_address,
        )

    @staticmethod
    def _setup_internal_socket(internal_socket: socket.socket) -> None:
        # TCP_NODELAY: small messages are not grouped to larger packages but sent immediately
        internal_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        platform = ExecutingPlatform.current()
        if platform is ExecutingPlatform.WINDOWS:
            # Windows: SO_REUSEADDR would allow other sockets to hijack an active port.
            # Request exclusive use explicitly (not the default on Windows).
            internal_socket.setsockopt(
                socket.SOL_SOCKET,
                # mypy complains on Linux because this is Windows exclusive
                socket.SO_EXCLUSIVEADDRUSE,  # type: ignore[attr-defined]
                1,
            )
        elif platform.is_posix:
            # BSD-style stacks refuse bind() while old connections on the port are in
            # TIME_WAIT (lasts ~1-4 min on the side that closed first).
            # SO_REUSEADDR allows rebinding immediately, e.g. after a server restart.
            internal_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def _has_internal_socket_peer(self) -> bool:
        try:
            self._internal_socket.getpeername()
            return True
        except socket.error:
            return False

    @override
    def is_connected(self) -> bool:
        return not self._closed.is_set() and (self._connected.is_set() or self._listening.is_set() or self._has_internal_socket_peer())

    def _bind(
        self,
        connection_address: ConnectionAddress,
    ) -> None:
        if self._bound.is_set():
            TCPSocket._logger.warning("Socket is already bound -> skipping binding to %s", connection_address)
            return
        self._bound.set()
        try:
            self._internal_socket.bind((connection_address.ip, connection_address.port))
            self._connection_address = connection_address
        except socket.error as e:
            TCPSocket._logger.error("Something went wrong binding to %s: %s", connection_address, e)
            self._bound.clear()
            raise e

    def _bind_and_listen(self) -> None:
        try:
            self._bind(self._connection_address)
            self._internal_socket.listen()
        except socket.error:
            self._internal_socket.close()
            raise
        self._internal_socket.settimeout(ACCEPT_TIMEOUT_IN_SECONDS)
        self._listening_on_connection.set()

    def _listen_on_connection_loop(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        TCPSocket._logger.debug("Starting listening on connection loop...")
        try:
            while not self._closed.is_set():
                self._accept_connection(channel_handler)
        finally:
            # closed first: a close() that finds the flag cleared relies on the port being free
            self._internal_socket.close()
            self._listening_on_connection.clear()
            self._accept_loop_ended.set()
        TCPSocket._logger.debug("Ended listening on connection loop.")

    def _accept_connection(self, channel_handler: ChannelHandler) -> None:
        try:
            connection, address = self._internal_socket.accept()
        except TimeoutError:
            return
        client_address = ConnectionAddress.of_raw_socket_address(address)
        TCPSocket._logger.debug("New connection on socket %s from %s", self._connection_address, client_address)
        channel = TCPSocket(_internal_socket=connection, _connection_address=client_address)
        connection_data = ConnectionData(channel=channel, client_address=client_address)
        threading.Thread(target=self._serve_channel, args=(channel_handler, connection_data), name=f"client-{client_address}").start()

    @staticmethod
    def _serve_channel(
        handler: ChannelHandler,
        connection_data: ConnectionData,
    ) -> None:
        try:
            handler(connection_data)
        except Exception as e:
            TCPSocket._logger.error("Client handler for %s failed: %s", connection_data.client_address, e)

    def listen_on_connection_loop_async(self, channel_handler: ChannelHandler) -> None:
        if self._listening_on_connection.is_set():
            TCPSocket._logger.warning("Socket is already listening on %s. So nothing is done.", self._connection_address)
            return
        self._bind_and_listen()
        threading.Thread(target=self._listen_on_connection_loop, args=(channel_handler,), daemon=False).start()

    def close(self) -> None:
        if self._closed.is_set():
            TCPSocket._logger.debug("Closing socket: socket already closed -> nothing done.")
            return
        self._closed.set()
        self._listening.clear()
        TCPSocket._logger.debug("Closing socket...")
        # a listening socket has no peer, its accept loop closes it
        if self._has_internal_socket_peer():
            try:
                self._internal_socket.shutdown(socket.SHUT_RDWR)
                TCPSocket._logger.debug("Closing socket: successfully sent SHUT_RDWR signal")
            except socket.error as e:
                TCPSocket._logger.warning("Something went wrong closing connection on %s: %s", self._connection_address, e)
        if self._listening_on_connection.is_set() and not self._accept_loop_ended.wait(timeout=ACCEPT_LOOP_END_TIMEOUT_IN_SECONDS):
            TCPSocket._logger.warning("Accept loop on %s did not end in time, so the port can still be in use.", self._connection_address)
            return
        TCPSocket._logger.debug("Closing socket...done.")

    def on_app_shutdown(self) -> None:
        self.close()

    def is_listening_event(self) -> ParallelEvent:
        return self._listening

    @override
    def is_listening_on_connection_event(self) -> ParallelEvent:
        return self._listening_on_connection

    def listen_on_message_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        if self._listening.is_set():
            TCPSocket._logger.warning("Socket is already listening to: %s. So nothing is done.", self._connection_address)
            return
        if self._start_listening_in_progress.is_set():
            TCPSocket._logger.warning("Socket already starts to listening to: %s. So nothing is done.", self._connection_address)
            return
        self._start_listening_in_progress.set()
        listen_thread = threading.Thread(target=self._listen_on_message_async, args=[on_message])
        listen_thread.start()

    def _listen_on_message_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        self._listening.set()
        self._start_listening_in_progress.clear()
        try:
            while not self._closed.is_set():
                message = self._listen_blocking()
                if message is not None:
                    on_message(message)
        except Exception:
            TCPSocket._logger.exception("Receive loop on %s failed -> closing the channel", self._connection_address)
        finally:
            self._listening.clear()
            self.close()

    def listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        if self._listening.is_set():
            TCPSocket._logger.warning("Socket is already listening to: %s. So nothing is done.", self._connection_address)
            return None
        if self._start_listening_in_progress.is_set():
            TCPSocket._logger.warning("Socket already starts to listening to: %s. So nothing is done.", self._connection_address)
            return None
        self._listening.set()
        try:
            return self._listen_blocking(timeout_in_seconds)
        finally:
            self._listening.clear()

    def _listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        timeout_buffer = self._internal_socket.gettimeout()
        self._internal_socket.settimeout(timeout_in_seconds)
        try:
            message: ReceivedBinaryMessage | None = self.receive()
        finally:
            self._internal_socket.settimeout(timeout_buffer)
        if not message:
            TCPSocket._logger.info("Received empty message -> closing connection")
            self.close()
            return None
        return message.to_esp_channel_message()

    def receive(self) -> ReceivedBinaryMessage | None:
        if self._closed.is_set():
            TCPSocket._logger.warning("Socket is in the progress of closing or already closed.")
            return None
        # no data at all between two messages is the closing signal, inside a message it is an error
        first_header_bytes = self._internal_socket.recv(binary_message_header.HEADER_BYTES)
        if not first_header_bytes:
            TCPSocket._logger.debug("Received no data")
            return None
        message_header = BinaryMessageHeader(
            first_header_bytes + self._receive_exactly(byte_count=binary_message_header.HEADER_BYTES - len(first_header_bytes)),
        )
        if not message_header:
            TCPSocket._logger.debug("Received no valid header")
            return None

        data = self._receive_exactly(byte_count=message_header.data_length)
        TCPSocket._logger.debug("Received message of type %s", message_header.message_type)
        return ReceivedBinaryMessage(
            _header=message_header,
            _data=data,
        )

    def _receive_exactly(
        self,
        byte_count: int,
    ) -> bytes:
        # recv() returns whatever has arrived so far, which can be any part of a message
        data = bytearray()
        while len(data) < byte_count:
            chunk = self._internal_socket.recv(byte_count - len(data))
            if not chunk:
                raise ConnectionError(f"Connection closed after {len(data)} of {byte_count} bytes.")
            data += chunk
        return bytes(data)

    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        if not self.is_connected():
            raise Exception("Socket is not connected.")
        raw_message = SimpleBinaryMessage.of_esp_channel_message(message=message).raw_message()
        try:
            self._internal_socket.sendall(raw_message)
        except Exception as e:
            connection_address = self._connection_address
            if not connection_address:
                raise e
            TCPSocket._logger.debug("Sending message to server failed - recreating the socket and try again. Error: %s", e)
            self._internal_socket.connect((connection_address.ip, connection_address.port))
            self._internal_socket.sendall(raw_message)

    @override
    def connect(self) -> None:
        if self._connected.is_set():
            TCPSocket._logger.debug("Socket is already connected.")
            return
        self._internal_socket.connect(
            (self._connection_address.ip, self._connection_address.port),
        )
        self._connected.set()

    @override
    def wait_for_finish(self) -> None:
        self._closed.wait()
