import socket
import threading
from dataclasses import dataclass, field
from typing import ClassVar, override

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_endpoint import ChannelHandler, ConnectionData, ESPChannelEndpoint
from ecosim_common.communication.socket.esp_socket import ESPSocket, create_internal_socket, is_raw_socket_connected
from ecosim_common.communication.socket.socket_channel import SocketChannel
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


@dataclass(frozen=True)
class EndpointSocket(ESPChannelEndpoint, ShutdownListener):
    _logger: ClassVar[ESPLogger] = ESPLogger("EndpointSocket")

    _connection_address: ConnectionAddress = field()
    _closed: threading.Event = field(default_factory=threading.Event)
    _listening: threading.Event = field(default_factory=threading.Event)
    _internal_socket: socket.socket = field(default_factory=create_internal_socket)

    def __post_init__(self) -> None:
        # SO_REUSEADDR: allow reusing the socket if it is in time-wait / time_out mode (the socket retains open
        #   about 2min in time_out mode after the socket is closed - this is an OS setting and handled by the OS)
        ShutdownManager().register_listener(self)
        self._internal_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    @override
    def listen_async(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        if self._listening.is_set():
            EndpointSocket._logger.warning(
                f"Socket is already listening to: {self._connection_address}. So nothing is done.",
            )
            return
        self._listening.set()
        listen_thread = threading.Thread(
            target=self._listen,
            args=(channel_handler,),
            daemon=False,
        )
        listen_thread.start()

    def _listen(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        with self._internal_socket:
            try:
                self._internal_socket.bind((self._connection_address.ip, self._connection_address.port))
            except socket.error as e:
                EndpointSocket._logger.error(f"Cannot listening on {self._connection_address}: {e}")
                raise e
            self._internal_socket.listen()
            EndpointSocket._logger.info(f"Socket listening on {self._connection_address}")
            while not self._closed.is_set():
                try:
                    connection, address = self._internal_socket.accept()
                except Exception as e:
                    if self._closed.is_set():
                        return
                    raise e
                if not connection:
                    EndpointSocket._logger.error(
                        f"Something went wrong accepting a connection on {self._connection_address}",
                    )
                    continue
                client_address = ConnectionAddress.of_raw_socket_address(address)
                if client_address.ip == self._connection_address.ip:
                    EndpointSocket._logger.info(
                        f"Socket listening on {self._connection_address} received a connection from itself - this is "
                        f"probably a shutdown trigger. If this message appears multiple times please investigate.",
                    )
                    continue
                EndpointSocket._logger.debug(
                    f"New connection on socket {self._connection_address} from {client_address}",
                )

                connection_data = ConnectionData(
                    channel=SocketChannel(ESPSocket(connection)),
                    client_address=client_address,
                )
                threading.Thread(
                    target=self._serve_channel,
                    args=(channel_handler, connection_data),
                    name=f"client-{connection_data.client_address}",
                ).start()
            EndpointSocket._logger.debug(f"Socket stopped listening on {self._connection_address}")

    @staticmethod
    def _serve_channel(handler: ChannelHandler, connection_data: ConnectionData) -> None:
        try:
            handler(connection_data)
        except Exception:
            EndpointSocket._logger.error(
                f"Client handler for {connection_data.client_address} failed",
            )

    @override
    def close(self) -> None:
        if self._listening.is_set():
            self._listening.clear()
            self._closed.set()
            if is_raw_socket_connected(self._internal_socket):
                try:
                    self._internal_socket.shutdown(socket.SHUT_RDWR)
                    self._internal_socket.close()
                except socket.error as e:
                    EndpointSocket._logger.error(f"Something went wrong closing connection on {self._connection_address}: {e}")

    def on_app_shutdown(self) -> None:
        self.close()
