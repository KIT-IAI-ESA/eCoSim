import struct
from typing import Any

from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType

HEADER_BYTES = 9
# > = the data should be packed using big-endian byte order (big-endian = most significant byte is stored first)
# L = unsigned long (4 bytes - 0 to 4.294.967.295)
# B = unsigned char (1 byte - 0 to 255)
# => in bytes: 4-1-4
# => the 'header' is 9 bytes
# the current format is [CORRELATION_ID][MESSAGE_TYPE][LENGTH]
BYTE_FORMAT = ">LBL"


class BinaryMessageHeader:
    def __init__(
        self,
        raw: bytes,
    ):
        self._raw = raw
        byte_array_received_data = bytearray(raw)
        if len(byte_array_received_data) != HEADER_BYTES:
            raise Exception(
                f"Invalid byte array received. Header must be {HEADER_BYTES} bytes but was {len(byte_array_received_data)}",
            )
        unpacked_values = struct.unpack(
            BYTE_FORMAT,
            byte_array_received_data[:HEADER_BYTES],
        )
        self.correlation_id: CorrelationId = CorrelationId.of_int(unpacked_values[0])
        self.message_type: MessageType = MessageType.of_int(unpacked_values[1])
        self.data_length: int = unpacked_values[2]

    def raw(self) -> bytes:
        return self._raw

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        return isinstance(other, BinaryMessageHeader) and self._raw == other._raw

    def __hash__(self) -> int:
        return hash(self._raw)
