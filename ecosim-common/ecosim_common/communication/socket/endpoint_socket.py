from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, override

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_endpoint import ChannelHandler, ESPChannelEndpoint
from ecosim_common.communication.socket.tcp_socket import TCPSocket
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


@dataclass(frozen=True)
class EndpointSocket(ESPChannelEndpoint, ShutdownListener):
    _logger: ClassVar[ESPLogger] = ESPLogger("EndpointSocket")

    _tcp_socket: TCPSocket = field()

    @staticmethod
    def for_connection_address(connection_address: ConnectionAddress) -> EndpointSocket:
        tcp_socket = TCPSocket.create(connection_address=connection_address)
        tcp_socket.enable_address_reuse()
        return EndpointSocket(_tcp_socket=tcp_socket)

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    @override
    def listen_on_connection_loop_async(
        self,
        channel_handler: ChannelHandler,
    ) -> None:
        self._tcp_socket.listen_on_connection_loop_async(channel_handler)

    @override
    def close(self) -> None:
        self._tcp_socket.close()

    def on_app_shutdown(self) -> None:
        self.close()

    def is_listening_event(self) -> ParallelEvent:
        return self._tcp_socket.is_listening_on_connection_event()
