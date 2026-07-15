from __future__ import annotations
from enum import Enum

from ecosim_common.tech.logger.logger import ESPLogger

_message_type_logger = ESPLogger("MessageType")


class MessageType(Enum):
    """
    The MessageType determines the type of channel messages.
    The internal representations are values from 0 to 255.
    This restriction will ensure certainty about the byte size and encoding for underlying protocols.
    """

    CLIENT_META_DATA_REQUEST = 0
    INTERFACE_REQUEST = 1
    INTERFACE_SETTINGS = 3
    SIMULATION_SETUP = 4
    SIMULATION_START = 5
    SIMULATION_STEP = 6
    SIMULATION_STOP = 7
    SIMULATION_STEP_BATCH = 8
    UNKNOWN = 255

    def to_int(self) -> int:
        """
        :return: unsigned char (i.e. 1 byte or values from 0 to 255)
        """
        return self.value

    @staticmethod
    def of_int(value: int) -> MessageType:
        if value < 0 or value > 255:
            _message_type_logger.error(
                f"Message type deserialization failed. Expected a value between 0 and 255 but was {value}.",
            )
            return MessageType.UNKNOWN
        if value == 0:
            return MessageType.CLIENT_META_DATA_REQUEST
        elif value == 1:
            return MessageType.INTERFACE_REQUEST
        elif value == 3:
            return MessageType.INTERFACE_SETTINGS
        elif value == 4:
            return MessageType.SIMULATION_SETUP
        elif value == 5:
            return MessageType.SIMULATION_START
        elif value == 6:
            return MessageType.SIMULATION_STEP
        elif value == 7:
            return MessageType.SIMULATION_STOP
        elif value == 8:
            return MessageType.SIMULATION_STEP_BATCH
        else:
            _message_type_logger.error(
                f"Message type deserialization failed. Value was in range (0-255) but is unknown: {value}.",
            )
            return MessageType.UNKNOWN
