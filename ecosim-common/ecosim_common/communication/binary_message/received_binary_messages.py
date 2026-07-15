import json

from ecosim_common.communication.binary_message.binary_message import BinaryMessage, BinaryMessageHeader
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson


class ReceivedBinaryMessage(BinaryMessage):
    def __init__(
        self,
        header: BinaryMessageHeader,
        data: bytes,
        connection: ConnectionAddress,
    ):
        self._header = header
        self._data = data
        self._connection = connection

    def raw_message(self) -> bytes:
        return self._header.raw() + self._data

    def header(self) -> BinaryMessageHeader:
        return self._header

    def raw_data(self) -> bytes:
        return self._data

    def to_esp_channel_message(self) -> ESPChannelMessage:
        return ESPChannelMessageJson(
            _type=self._header.message_type,
            _correlation_id=self._header.correlation_id,
            _payload=json.loads(self._data),
        )
