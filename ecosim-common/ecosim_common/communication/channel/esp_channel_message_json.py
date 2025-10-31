from __future__ import annotations
from dataclasses import dataclass, field
from typing import override, Type, Any

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.message_data import MessageData, MESSAGE_DATA
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType


@dataclass(frozen=True)
class ESPChannelMessageJson(ESPChannelMessage):
    _type: MessageType = field()
    _payload: Any = field()
    _correlation_id: CorrelationId = field()

    @staticmethod
    def empty_answer(
            request_message: ESPChannelMessage,
    ) -> ESPChannelMessageJson:
        return ESPChannelMessageJson(
            _type=request_message.type(),
            _correlation_id=request_message.correlation_id(),
            _payload="",
        )

    @staticmethod
    def answer_with_payload(
            request_message: ESPChannelMessage,
            payload: MessageData,
    ) -> ESPChannelMessageJson:
        return ESPChannelMessageJson(
            _type=request_message.type(),
            _correlation_id=request_message.correlation_id(),
            _payload=payload.to_json(),
        )

    @staticmethod
    def create(
            type: MessageType,
            payload: MessageData,
            correlation_id: CorrelationId | None = None,
    ) -> ESPChannelMessageJson:
        return ESPChannelMessageJson(
            _type=type,
            _correlation_id=correlation_id or CorrelationId.default_id(),
            _payload=payload.to_json(),
        )

    @staticmethod
    def empty(
            type: MessageType,
            correlation_id: CorrelationId | None = None,
    ) -> ESPChannelMessageJson:
        return ESPChannelMessageJson(
            _type=type,
            _correlation_id=correlation_id or CorrelationId.default_id(),
            _payload="",
        )

    @override
    def payload(
        self,
        clazz: Type[MESSAGE_DATA] | None = None,
    ) -> MESSAGE_DATA | Any:
        if clazz is None:
            return self._payload
        return clazz.of_json(self._payload)

    @override
    def type(self) -> MessageType:
        return self._type

    @override
    def correlation_id(self) -> CorrelationId:
        return self._correlation_id
