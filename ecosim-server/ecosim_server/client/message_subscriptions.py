from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.client.client_message import ClientMessage

_logger = ESPLogger("MessageSubscriptions")

MessageQueue = ESPQueue[ClientMessage]


@dataclass(frozen=True)
class MessageSubscriptionKey:
    """What a subscriber wants to receive. There is at most one queue per key."""

    client_ids: Tuple[ClientID, ...] = field()
    message_types: Tuple[MessageType, ...] = field()

    def matches(
        self,
        client_id: ClientID,
        message_type: MessageType,
    ) -> bool:
        return client_id in self.client_ids and message_type in self.message_types


@dataclass
class MessageSubscriptions:
    _queues: ESPMap[MessageSubscriptionKey, MessageQueue] = field()
    _communication_protocol: CommunicationProtocol = field()

    @staticmethod
    def for_communication_protocol(communication_protocol: CommunicationProtocol) -> MessageSubscriptions:
        return MessageSubscriptions(
            _queues=ESPMap.of_type(
                map_type=ESPStructureType.default_for_communication_protocol(communication_protocol),
            ),
            _communication_protocol=communication_protocol,
        )

    def create_queue_if_not_exists_for(
        self,
        key: MessageSubscriptionKey,
    ) -> MessageQueue | None:
        """Returns False if something is already subscribed on 'key' - that subscription is kept."""
        with self._queues.transaction() as queues:
            if key in queues:
                _logger.warning("You can only subscribe once on %s | %s. The new subscription is discarded.", key.client_ids, key.message_types)
                return None
            queues[key] = ESPQueue.of_communication_protocol(self._communication_protocol)
            return queues[key]

    def remove(
        self,
        key: MessageSubscriptionKey,
    ) -> None:
        with self._queues.transaction() as queues:
            queues.pop(key, None)

    def queue_for(
        self,
        client_id: ClientID,
        message_type: MessageType,
    ) -> MessageQueue | None:
        for key, queue in self._queues.get_snapshot().items():
            if key.matches(client_id, message_type):
                return queue
        return None
