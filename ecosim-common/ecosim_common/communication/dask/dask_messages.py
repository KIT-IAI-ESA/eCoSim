import json
import struct
from abc import ABC, abstractmethod
from typing import Any

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.channel.connection_address import ConnectionAddress


class DaskMessageHeader:
    def __init__(self,
                 raw: bytes
                 ):
        self._raw = raw
        byte_array_received_data = bytearray(raw)
        if len(byte_array_received_data) != DaskMessage.HEADER_BYTES:
            raise Exception(
                f"Invalid byte array received. "
                f"Header must be {DaskMessage.HEADER_BYTES} bytes but was {len(byte_array_received_data)}")
        unpacked_values = struct.unpack(DaskMessage.BYTE_FORMAT,
                                        byte_array_received_data[:DaskMessage.HEADER_BYTES])
        self.correlation_id: CorrelationId = CorrelationId.of_int(unpacked_values[0])
        self.message_type: MessageType = MessageType.of_int(unpacked_values[1])
        self.data_length: int = unpacked_values[2]

    def raw(self) -> bytes:
        return self._raw

    def __eq__(self,
               other: Any,
               ) -> bool:
        return (isinstance(other, DaskMessageHeader) and
                self._raw == other._raw)

    def __hash__(self) -> int:
        return hash(self._raw)


class DaskMessage(ABC):
    HEADER_BYTES = 9
    ENCODING = 'utf-8'
    BYTE_FORMAT = '>LBL'

    @abstractmethod
    def raw_message(self) -> bytes:
        pass

    @abstractmethod
    def header(self) -> DaskMessageHeader:
        pass

    @abstractmethod
    def raw_data(self) -> bytes:
        pass

    def decode_data(self) -> str:
        return self.raw_data().decode(DaskMessage.ENCODING)


class ReceivedMessage(DaskMessage):

    def __init__(self,
                 header: DaskMessageHeader,
                 data: bytes,
                 connection: ConnectionAddress
                 ):
        self._header = header
        self._data = data
        self._connection = connection

    def raw_message(self) -> bytes:
        return self._header.raw() + self._data

    def header(self) -> bytes:
        return self._data

    def to_esp_channel_message(self) -> ESPChannelMessage:
        return ESPChannelMessageJson(
            _type=self._header.message_type,
            _correlation_id=self._header.correlation_id,
            _payload=json.loads(self._data),
        )
