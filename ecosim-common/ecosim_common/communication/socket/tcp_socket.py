from __future__ import annotations

import socket
import threading
from dataclasses import dataclass, field
from typing import Callable, ClassVar

from ecosim_common.communication.binary_message.binary_message import BinaryMessage, BinaryMessageHeader
from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.binary_message.simple_binary_message import SimpleBinaryMessage
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_endpoint import ChannelHandler, ConnectionData
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


@dataclass
class TCPSocket(ShutdownListener):
    _logger: ClassVar[ESPLogger] = ESPLogger("TCPSocket")

    _internal_socket: socket.socket = field()
    _connection_address: ConnectionAddress = field()
    _closed: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _connected: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _bound: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _listening: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _listening_on_connection: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())
    _start_listening_in_progress: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    @staticmethod
    def create(connection_address: ConnectionAddress) -> TCPSocket:
        # AF_INET: address family internet => socket is using IPv4
        # SOCK_STREAM: byte-stream communication (by TCP)
        internal_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # TCP_NODELAY: small messages are not grouped to larger packages but sent immediately
        internal_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return TCPSocket(
            _internal_socket=internal_socket,
            _connection_address=connection_address,
        )

    def _is_internal_socket_listening(self) -> bool:
        return not self._internal_socket.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN)

    def _has_internal_socket_peer(self) -> bool:
        try:
            self._internal_socket.getpeername()
            return True
        except socket.error:
            return False

    def is_internal_socket_closed(self) -> bool:
        return self._internal_socket.fileno() == -1

    def is_connected(self) -> bool:
        return not self._closed.is_set() and (self._connected.is_set() or self._listening.is_set() or self._has_internal_socket_peer())

    def enable_address_reuse(self) -> None:
        # SO_REUSEADDR: allow reusing the socket if it is in time-wait / time_out mode (the socket retains open
        #   about 2min in time_out mode after the socket is closed - this is an OS setting and handled by the OS)
        self._internal_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def _bind(
        self,
        connection_address: ConnectionAddress,
    ) -> None:
        if self._bound.is_set():
            TCPSocket._logger.warning(
                f"Socket is already bound -> skipping binding to {connection_address}",
            )
            return
        self._bound.set()
        try:
            self._internal_socket.bind((connection_address.ip, connection_address.port))
            self._connection_address = connection_address
        except socket.error as e:
            TCPSocket._logger.error(
                f"Something went wrong binding to {connection_address}: {e}",
            )
            self._bound.clear()
            raise e

    def _listen_on_connection_loop(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        TCPSocket._logger.debug("Starting listening on connection loop...")
        with self._internal_socket:
            connection_address = self._connection_address
            if not connection_address:
                TCPSocket._logger.error(
                    "No connection address is set -> cannot listen on socket.",
                )
                return
            if not self._bound.is_set():
                self._bind(connection_address)
            self._listening_on_connection.set()
            self._internal_socket.listen()
            while not self._closed.is_set():
                try:
                    connection, address = self._internal_socket.accept()
                except Exception as e:
                    if self._closed.is_set():
                        return
                    raise e
                if not connection:
                    TCPSocket._logger.error(
                        f"Something went wrong accepting a connection on {connection_address}",
                    )
                    continue
                client_address = ConnectionAddress.of_raw_socket_address(address)
                if client_address.ip == connection_address.ip:
                    TCPSocket._logger.info(
                        f"Socket listening on {connection_address} received a connection from itself - this is "
                        f"probably a shutdown trigger. If this message appears multiple times please investigate.",
                    )
                    continue
                TCPSocket._logger.debug(
                    f"New connection on socket {connection_address} from {client_address}",
                )

                from ecosim_common.communication.socket.socket_channel import SocketChannel

                connection_data = ConnectionData(
                    channel=SocketChannel(
                        _internal_socket=TCPSocket(
                            _internal_socket=connection,
                            _connection_address=client_address,
                        ),
                    ),
                    client_address=client_address,
                )
                threading.Thread(
                    target=self._serve_channel,
                    args=(channel_handler, connection_data),
                    name=f"client-{connection_data.client_address}",
                ).start()
            self._listening_on_connection.clear()
        TCPSocket._logger.debug("Ended listening on connection loop.")

    @staticmethod
    def _serve_channel(
        handler: ChannelHandler,
        connection_data: ConnectionData,
    ) -> None:
        try:
            handler(connection_data)
        except Exception as e:
            TCPSocket._logger.error(
                f"Client handler for {connection_data.client_address} failed: {e}",
            )

    def listen_on_connection_loop_async(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        listen_thread = threading.Thread(
            target=self._listen_on_connection_loop,
            args=(channel_handler,),
            daemon=False,
        )
        listen_thread.start()

    def close(self) -> None:
        if self._closed.is_set():
            TCPSocket._logger.debug("Closing socket: socket already closed -> nothing done.")
            return
        self._closed.set()
        self._listening.clear()
        TCPSocket._logger.debug("Closing socket...")
        if self._is_internal_socket_listening() or self._has_internal_socket_peer() or self._listening_on_connection.is_set():
            TCPSocket._logger.debug(
                f"Closing socket: internal listening: {self._is_internal_socket_listening()} | peers: {self._has_internal_socket_peer()} | "
                + f"listening on connection: {self._listening_on_connection.is_set()}",
            )
            self._listening_on_connection.clear()
            try:
                self._internal_socket.shutdown(socket.SHUT_RDWR)
                TCPSocket._logger.debug("Closing socket: successfully sent SHUT_RDWR signal")
            except socket.error as e:
                TCPSocket._logger.error(f"Something went wrong closing connection on {self._connection_address}: {e}")
        TCPSocket._logger.debug("Closing socket...done.")

    def on_app_shutdown(self) -> None:
        self.close()

    def is_listening_event(self) -> ParallelEvent:
        return self._listening

    def is_listening_on_connection_event(self) -> ParallelEvent:
        return self._listening_on_connection

    def listen_on_message_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        if self._listening.is_set():
            TCPSocket._logger.warning(
                f"Socket is already listening to: {self._connection_address}. So nothing is done.",
            )
            return
        if self._start_listening_in_progress.is_set():
            TCPSocket._logger.warning(
                f"Socket already starts to listening to: {self._connection_address}. So nothing is done.",
            )
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
        while not self._closed.is_set():
            message = self._listen_blocking()
            if message is not None:
                on_message(message)
        self._listening.clear()

    def listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        if self._listening.is_set():
            TCPSocket._logger.warning(
                f"Socket is already listening to: {self._connection_address}. So nothing is done.",
            )
            return None
        if self._start_listening_in_progress.is_set():
            TCPSocket._logger.warning(
                f"Socket already starts to listening to: {self._connection_address}. So nothing is done.",
            )
            return None
        self._listening.set()
        message = self._listen_blocking(timeout_in_seconds)
        self._listening.clear()
        return message

    def _listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        timeout_buffer = self._internal_socket.gettimeout()
        self._internal_socket.settimeout(timeout_in_seconds)
        message: ReceivedBinaryMessage | None = self.receive()
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
        raw_header = self._internal_socket.recv(BinaryMessage.HEADER_BYTES)
        if not raw_header:
            TCPSocket._logger.debug("Received no data")
            return None
        message_header = BinaryMessageHeader(raw_header)
        if not message_header:
            TCPSocket._logger.debug("Received no valid header")
            return None

        data: bytes = b""
        while len(data) < message_header.data_length:
            chunk = self._internal_socket.recv(message_header.data_length - len(data))
            if not chunk:
                raise ConnectionError("Error while receiving junks.")
            data += chunk
        TCPSocket._logger.debug(
            f"Received message of type {message_header.message_type}",
        )
        return ReceivedBinaryMessage(
            message_header,
            data,
            self._connection_address or ConnectionAddress.of_socket(self._internal_socket),
        )

    def is_closed_event(self) -> ParallelEvent:
        return self._closed

    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        if not self.is_connected():
            raise Exception("Socket is not connected.")
        raw_message = SimpleBinaryMessage.of_esp_channel_message(message=message).raw_message()
        try:
            self._internal_socket.send(raw_message)
        except Exception as e:
            connection_address = self._connection_address
            if not connection_address:
                raise e
            TCPSocket._logger.debug(
                f"Sending message to server failed - recreating the socket and try again. Error: {e}",
            )
            self._internal_socket.connect((connection_address.ip, connection_address.port))
            self._internal_socket.send(raw_message)

    def connect(self) -> None:
        if self._connected.is_set():
            TCPSocket._logger.debug("Socket is already connected.")
            return
        self._internal_socket.connect(
            (self._connection_address.ip, self._connection_address.port),
        )
        self._connected.set()
