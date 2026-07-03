from __future__ import annotations

import json
import struct
from typing import Any

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.socket.socket_messages import SocketMessage, SocketMessageHeader


# TODO_AFTER_MERGE: common abstraction between SocketMessage and DaskMessage (something like BinaryMessage)
class SimpleSocketMessage(SocketMessage):

    @staticmethod
    def of_esp_channel_message(message: ESPChannelMessage) -> SimpleSocketMessage:
        return SimpleSocketMessage(
            _type=message.type(),
            _correlation_id=message.correlation_id(),
            _payload=json.dumps(message.payload()).encode("utf-8"),
        )

    @staticmethod
    def create(
            type: MessageType,
            correlation_id: CorrelationId,
            payload: Any,
    ) -> SimpleSocketMessage:
        return SimpleSocketMessage(
            _type=type,
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

    def bytecode(self) -> bytearray:
        data_length = self.length
        bytecode = bytearray(SocketMessage.HEADER_BYTES + data_length)
        bytecode[0:SocketMessage.HEADER_BYTES] = self._raw_header()
        bytecode[SocketMessage.HEADER_BYTES:] = bytearray(self._payload)
        return bytecode

    def _raw_header(self) -> bytes:
        return struct.pack(
            SocketMessage.BYTE_FORMAT,
            self._correlation_id.to_int(),
            self._type.to_int(),
            self.length,
        )

    def raw_message(self) -> bytes:
        return self.bytecode()

    def header(self) -> SocketMessageHeader:
        return SocketMessageHeader(self._raw_header())

    def raw_data(self) -> bytes:
        return self._payload
