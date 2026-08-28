from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field

from ecosim_common.communication.binary_message import binary_message_header
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType


@dataclass(frozen=True)
class SimpleBinaryMessage:
    _type: MessageType = field()
    _correlation_id: CorrelationId = field()
    _payload: bytes = field()
    _length: int = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_length", len(self._payload))

    @staticmethod
    def of_esp_channel_message(message: ESPChannelMessage) -> SimpleBinaryMessage:
        return SimpleBinaryMessage(
            _type=message.type(),
            _correlation_id=message.correlation_id(),
            _payload=json.dumps(message.payload()).encode("utf-8"),
        )

    def bytecode(self) -> bytes:
        data_length = self._length
        bytecode = bytearray(binary_message_header.HEADER_BYTES + data_length)
        bytecode[0 : binary_message_header.HEADER_BYTES] = self._raw_header()
        bytecode[binary_message_header.HEADER_BYTES :] = bytearray(self._payload)
        return bytes(bytecode)

    def _raw_header(self) -> bytes:
        return struct.pack(
            binary_message_header.BYTE_FORMAT,
            self._correlation_id.to_int(),
            self._type.to_int(),
            self._length,
        )

    def raw_message(self) -> bytes:
        return self.bytecode()
