import socket
import threading

from ecosim_common.communication.binary_message.binary_message import (
    BinaryMessage,
    BinaryMessageHeader,
)
from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.tech.atomic.atomic_integer import AtomicInteger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


def create_internal_socket() -> socket.socket:
    # AF_INET: address family internet => socket is using IPv4
    # SOCK_STREAM: byte-stream communication (by TCP)
    internal_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # TCP_NODELAY: small messages are not grouped to larger packages but sent immediately
    internal_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return internal_socket


def is_raw_socket_connected(raw_socket: socket.socket) -> bool:
    try:
        raw_socket.getsockname()
        return True
    except socket.error:
        return False


class ESPSocket(ShutdownListener):
    _logger = ESPLogger("ESPSocket")

    def __init__(
        self,
        internal_socket: socket.socket,
    ):
        ShutdownManager().register_listener(self)
        self._closing_calls = AtomicInteger.thread(0)
        self._closed: threading.Event = threading.Event()
        self._internal_socket = internal_socket
        self._connected: bool = is_raw_socket_connected(internal_socket)

    def on_app_shutdown(self) -> None:
        if not self._closed.is_set():
            ESPSocket._logger.info(
                "Internal shutdown signal triggered - closing socket...",
            )
            self.close()

    def connect(
        self,
        connection_address: ConnectionAddress,
    ) -> None:
        self._internal_socket.connect(
            (connection_address.ip, connection_address.port),
        )
        self._connected = True

    def is_connected(self) -> bool:
        return self._connected

    def connection_address(self) -> ConnectionAddress:
        return ConnectionAddress.of_socket(self._internal_socket)

    def close(self) -> None:
        if self._closed.is_set():
            if not ShutdownManager().shutdown_event.is_set():
                # if it is during shutdown no warning is printed since this is most likely due to race conditions
                ESPSocket._logger.warning("Tried to close an already closed socket.")
            return
        closing_calls = self._closing_calls.inc()
        ESPSocket._logger.debug(
            f"Closing socket {self.connection_address()}... (_closing_calls={closing_calls})",
        )
        self._closed.set()
        self._connected = False
        if closing_calls == 1:
            try:
                self._internal_socket.shutdown(socket.SHUT_RDWR)
            except Exception as e:
                if not ShutdownManager().shutdown_event.is_set() or self._closing_calls.value == 1:
                    # if it is during shutdown AND 'close' is called more than once,
                    # no error is printed since this is most likely due to race conditions
                    ESPSocket._logger.error(
                        f"Failed to send shutdown to socket due to '{e}'. (_closing_calls={self._closing_calls.value}) "
                        + "-> trying to force close socket.",
                    )
                    try:
                        self._internal_socket.close()
                        ESPSocket._logger.info(
                            f"Successfully force closed socket. (_closing_calls: {self._closing_calls.value})",
                        )
                    except Exception as e:
                        ESPSocket._logger.error(
                            f"Failed to force close socket due to '{e}'. (_closing_calls: {self._closing_calls.value})",
                        )
                return
            self._internal_socket.close()
            ESPSocket._logger.info("Successfully closed socket.")
        else:
            ESPSocket._logger.info("Socket is already in closing process.")

    def send(
        self,
        message: BinaryMessage,
    ) -> None:
        if self._closed.is_set():
            raise Exception("Socket is in the progress of closing or already closed.")
        ESPSocket._logger.debug(f"Sending message {message.header().message_type}")
        ESPSocket.send_to_socket(self._internal_socket, message)

    def receive(self) -> ReceivedBinaryMessage | None:
        if self._closed.is_set():
            raise Exception("Socket is in the progress of closing or already closed.")
        return ESPSocket.receive_from_socket(self._internal_socket)

    @staticmethod
    def send_to_socket(
        connection: socket.socket,
        message: BinaryMessage,
    ) -> None:
        connection.send(message.raw_message())

    @staticmethod
    def receive_from_socket(connection: socket.socket) -> ReceivedBinaryMessage | None:
        raw_header = connection.recv(BinaryMessage.HEADER_BYTES)
        if not raw_header:
            ESPSocket._logger.debug("Received no data")
            return None
        message_header = BinaryMessageHeader(raw_header)
        if not message_header:
            ESPSocket._logger.debug("Received no valid header")
            return None

        data: bytes = b""
        while len(data) < message_header.data_length:
            chunk = connection.recv(message_header.data_length - len(data))
            if not chunk:
                raise ConnectionError("Error while receiving junks.")
            data += chunk
        ESPSocket._logger.debug(
            f"Received message of type {message_header.message_type}",
        )
        return ReceivedBinaryMessage(
            message_header,
            data,
            ConnectionAddress.of_socket(connection),
        )
