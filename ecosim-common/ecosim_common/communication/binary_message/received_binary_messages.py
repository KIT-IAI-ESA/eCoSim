import json
from dataclasses import dataclass, field

from ecosim_common.communication.binary_message.binary_message_header import BinaryMessageHeader
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson


@dataclass(frozen=True)
class ReceivedBinaryMessage:
    _header: BinaryMessageHeader = field()
    _data: bytes = field()
    _connection: ConnectionAddress = field()

    def to_esp_channel_message(self) -> ESPChannelMessage:
        return ESPChannelMessageJson(
            _type=self._header.message_type,
            _correlation_id=self._header.correlation_id,
            _payload=json.loads(self._data),
        )
