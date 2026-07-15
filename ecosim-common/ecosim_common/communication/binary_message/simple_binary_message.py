from __future__ import annotations

import json
import struct
from typing import Any

from ecosim_common.communication.binary_message.binary_message import BinaryMessage, BinaryMessageHeader
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType


class SimpleBinaryMessage(BinaryMessage):
    @staticmethod
    def of_esp_channel_message(message: ESPChannelMessage) -> SimpleBinaryMessage:
        return SimpleBinaryMessage(
            _type=message.type(),
            _correlation_id=message.correlation_id(),
            _payload=json.dumps(message.payload()).encode("utf-8"),
        )

    @staticmethod
    def create(
        message_type: MessageType,
        correlation_id: CorrelationId,
        payload: Any,
    ) -> SimpleBinaryMessage:
        return SimpleBinaryMessage(
            _type=message_type,
            _correlation_id=correlation_id,
            _payload=json.dumps(payload).encode("utf-8"),
        )

    def __init__(
        self,
        _type: MessageType,
        _correlation_id: CorrelationId,
        _payload: bytes,
    ):
        self._type = _type
        self._correlation_id = _correlation_id
        self._payload = _payload
        self.length = len(_payload)

    def bytecode(self) -> bytes:
        data_length = self.length
        bytecode = bytearray(BinaryMessage.HEADER_BYTES + data_length)
        bytecode[0 : BinaryMessage.HEADER_BYTES] = self._raw_header()
        bytecode[BinaryMessage.HEADER_BYTES :] = bytearray(self._payload)
        return bytes(bytecode)

    def _raw_header(self) -> bytes:
        return struct.pack(
            BinaryMessage.BYTE_FORMAT,
            self._correlation_id.to_int(),
            self._type.to_int(),
            self.length,
        )

    def raw_message(self) -> bytes:
        return self.bytecode()

    def header(self) -> BinaryMessageHeader:
        return BinaryMessageHeader(self._raw_header())

    def raw_data(self) -> bytes:
        return self._payload
