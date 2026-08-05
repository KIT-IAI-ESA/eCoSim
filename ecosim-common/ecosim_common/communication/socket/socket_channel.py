from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, ClassVar, override

from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.binary_message.simple_binary_message import SimpleBinaryMessage
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.socket.esp_socket import ESPSocket
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


@dataclass
class SocketChannel(ESPChannel):
    _logger: ClassVar[ESPLogger] = ESPLogger("SocketChannel")

    _internal_socket: ESPSocket
    _is_finished: ParallelEvent = field(default_factory=lambda: ParallelEvent.thread())

    @override
    def close(self) -> None:
        if not self._internal_socket.is_connected() or self._is_finished.is_set():
            return
        self._is_finished.set()
        connection_address = self._internal_socket.connection_address()
        SocketChannel._logger.debug(f"Closing connection to socket {connection_address}...")
        self._internal_socket.close()
        SocketChannel._logger.info(f"Connection to socket {connection_address} closed.")

    @override
    def listen_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        listen_thread = threading.Thread(target=self._listen, args=[on_message])
        listen_thread.start()

    def _listen(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        while not self._is_finished.is_set():
            message = self.listen_blocking()
            if message is not None:
                on_message(message)

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
        message: ReceivedBinaryMessage | None = self._internal_socket.receive()
        if not message:
            SocketChannel._logger.info("Received empty message -> closing connection")
            self._is_finished.set()
            return None
        return message.to_esp_channel_message()

    @override
    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        if not self._internal_socket.is_connected():
            raise Exception("Socket already closed")
        try:
            self._internal_socket.send(
                SimpleBinaryMessage.of_esp_channel_message(message=message),
            )
        except Exception as e:
            SocketChannel._logger.debug(
                f"Sending message to server failed - recreating the socket and try again. Error: {e}",
            )
            self._internal_socket.connect(connection_address=self._internal_socket.connection_address())
            self._internal_socket.send(
                SimpleBinaryMessage.of_esp_channel_message(message=message),
            )
