import json
import struct
from abc import ABC, abstractmethod
from typing import Any

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.channel.connection_address import ConnectionAddress


class SocketMessageHeader:

    def __init__(self,
                 raw: bytes
                 ):
        self._raw = raw
        byte_array_received_data = bytearray(raw)
        if len(byte_array_received_data) != SocketMessage.HEADER_BYTES:
            raise Exception(
                f"Invalid byte array received. "
                f"Header must be {SocketMessage.HEADER_BYTES} bytes but was {len(byte_array_received_data)}")
        unpacked_values = struct.unpack(SocketMessage.BYTE_FORMAT,
                                        byte_array_received_data[:SocketMessage.HEADER_BYTES])
        self.correlation_id: CorrelationId = CorrelationId.of_int(unpacked_values[0])
        self.message_type: MessageType = MessageType.of_int(unpacked_values[1])
        self.data_length: int = unpacked_values[2]

    def raw(self) -> bytes:
        return self._raw

    def __eq__(self,
               other: Any,
               ) -> bool:
        return (isinstance(other, SocketMessageHeader) and
                self._raw == other._raw)

    def __hash__(self) -> int:
        return hash(self._raw)


class SocketMessage(ABC):
    HEADER_BYTES = 9
    ENCODING = 'utf-8'
    # > = the data should be packed using big-endian byte order (big-endian = most significant byte is stored first)
    # L = unsigned long (4 bytes - 0 to 4.294.967.295)
    # B = unsigned char (1 byte - 0 to 7)
    # H = unsigned short (2 bytes - 0 to 255)
    # => in bytes: 4-1-4
    # => the 'header' is 9 bytes
    # the current format is [CORRELATION_ID][MESSAGE_TYPE][LENGTH]
    BYTE_FORMAT = '>LBL'

    @abstractmethod
    def raw_message(self) -> bytes:
        pass

    @abstractmethod
    def header(self) -> SocketMessageHeader:
        pass

    @abstractmethod
    def raw_data(self) -> bytes:
        pass

    def decoded_data(self) -> str:
        return self.raw_data().decode(SocketMessage.ENCODING)


class ReceivedMessage(SocketMessage):

    def __init__(self,
                 header: SocketMessageHeader,
                 data: bytes,
                 connection: ConnectionAddress
                 ):
        self._header = header
        self._data = data
        self._connection = connection

    def raw_message(self) -> bytes:
        return self._header.raw() + self._data

    def header(self) -> SocketMessageHeader:
        return self._header

    def raw_data(self) -> bytes:
        return self._data

    def to_esp_channel_message(self) -> ESPChannelMessage:
        return ESPChannelMessageJson(
            _type=self._header.message_type,
            _correlation_id=self._header.correlation_id,
            _payload=json.loads(self._data),
        )
