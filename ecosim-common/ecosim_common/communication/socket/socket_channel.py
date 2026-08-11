from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, ClassVar, override

from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.socket.tcp_socket import TCPSocket
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


@dataclass
class SocketChannel(ESPChannel):
    _logger: ClassVar[ESPLogger] = ESPLogger("SocketChannel")

    _internal_socket: TCPSocket

    @override
    def close(self) -> None:
        self._internal_socket.close()

    @override
    def listen_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        self._internal_socket.listen_on_message_async(on_message)

    @override
    def wait_for_finish(
        self,
        timeout_in_seconds: int | None = None,
    ) -> None:
        self._internal_socket.is_closed_event().wait(timeout_in_seconds)

    @override
    def listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        return self._internal_socket.listen_blocking(timeout_in_seconds)

    @override
    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        return self._internal_socket.send(message)

    @override
    def is_listening_event(self) -> ParallelEvent:
        return self._internal_socket.is_listening_event()
