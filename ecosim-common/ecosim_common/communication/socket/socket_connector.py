import socket
import time
from dataclasses import dataclass

from typing_extensions import override

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.socket.socket_channel import SocketChannel
from ecosim_common.communication.socket.esp_socket import create_internal_socket, ESPSocket
from ecosim_common.tech.logger.logger import ESPLogger


@dataclass(frozen=True)
class SocketConnector(ESPChannelConnector):
    _logger = ESPLogger("SocketConnector")

    @override
    def connect(
        self,
        connection_address: ConnectionAddress,
        timeout_in_seconds: int = 30,
    ) -> ESPChannel:
        start_time = time.time()
        esp_socket = ESPSocket(internal_socket=create_internal_socket())
        connected: bool = False
        while not connected and (time.time() - start_time) < timeout_in_seconds:
            try:
                esp_socket.connect(connection_address)
                connected = True
            except socket.error as e:
                SocketConnector._logger.warning(
                    f"Cannot connect to socket - trying in sum for {timeout_in_seconds}s. Error: {e}",
                )
                time.sleep(1)
        if not connected:
            raise ConnectionError(f"Could not connect to socket {connection_address}")
        SocketConnector._logger.info(f"Connected to socket successfully: {connection_address}")
        return SocketChannel(esp_socket)
