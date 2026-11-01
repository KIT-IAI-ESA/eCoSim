from __future__ import annotations

import time
from typing import Any, Type

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.message_data import MESSAGE_DATA
from ecosim_common.config.client_id import ClientID


class ClientMessage:
    """A message together with the client it came from and the moment it arrived."""

    def __init__(
        self,
        client_id: ClientID,
        message: ESPChannelMessage,
        send_failure: str | None = None,
    ):
        self.time_stamp_ns = time.time_ns()
        self.client_id = client_id
        self.message = message
        # set when this is no received message but tells whoever waits for the answer that the send failed
        self.send_failure = send_failure

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        return (
            isinstance(other, ClientMessage)
            and self.time_stamp_ns == other.time_stamp_ns
            and self.client_id == other.client_id
            and self.message.type() == other.message.type()
            and self.message.correlation_id() == other.message.correlation_id()
            and self.message.payload() == other.message.payload()
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.time_stamp_ns,
                self.client_id,
                self.message.type(),
                self.message.correlation_id(),
                self.message.payload(),
            ),
        )

    def payload(
        self,
        clazz: Type[MESSAGE_DATA],
    ) -> MESSAGE_DATA:
        return self.message.payload(clazz)
