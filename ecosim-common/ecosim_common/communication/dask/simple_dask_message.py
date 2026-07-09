import json
import struct
from typing import Any

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.dask.dask_messages import DaskMessage, DaskMessageHeader
from ecosim_common.communication.message_type import MessageType


# TODO_AFTER_MERGE: common abstraction between SocketMessage and DaskMessage (something like BinaryMessage)
class SimpleDaskMessage(DaskMessage):
    @staticmethod
    def of_esp_channel_message(message: ESPChannelMessage) -> SimpleDaskMessage:
        return SimpleDaskMessage(
            _type=message.type(),
            _correlation_id=message.correlation_id(),
            _payload=json.dumps(message.payload()).encode("utf-8"),
        )

    @staticmethod
    def create(
        message_type: MessageType,
        correlation_id: CorrelationId,
        payload: Any,
    ) -> SimpleDaskMessage:
        return SimpleDaskMessage(
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
        bytecode = bytearray(DaskMessage.HEADER_BYTES + data_length)
        bytecode[0 : DaskMessage.HEADER_BYTES] = self._raw_header()
        bytecode[DaskMessage.HEADER_BYTES :] = bytearray(self._payload)
        return bytes(bytecode)

    def _raw_header(self) -> bytes:
        return struct.pack(
            DaskMessage.BYTE_FORMAT,
            self._correlation_id.to_int(),
            self._type.to_int(),
            self.length,
        )

    def raw_message(self) -> bytes:
        return self.bytecode()

    def header(self) -> DaskMessageHeader:
        return DaskMessageHeader(self._raw_header())

    def raw_data(self) -> bytes:
        return self._payload
