from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import Any

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.message_type import MessageType


@dataclass(frozen=True)
class ClientConnection(AbstractContextManager["ClientConnection"]):
    _channel: ESPChannel = field()
    address: ConnectionAddress = field()

    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        self._channel.send(message)

    def receive(
        self,
        expected_type: MessageType | None = None,
    ) -> ESPChannelMessage | None:
        message = self._channel.listen_blocking()
        if expected_type is not None and (message is None or message.type() != expected_type):
            received_type: str = "None"
            if message is not None:
                received_type = str(message.type())
            raise TypeError(f"Expected {expected_type} but received {received_type}")
        return message

    def close(self) -> None:
        self._channel.close()

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()
