from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.structures.esp_list import ESPList
from ecosim_server.client.client_message import ClientMessage
from ecosim_server.client.message_subscriptions import MessageQueue, MessageSubscriptionKey, MessageSubscriptions

_message_buffer_logger = ESPLogger("MessageBuffer")


@dataclass
class ClientMessageBuffer:
    """
    Hands every incoming message to the queue subscribed on it, or keeps it until someone subscribes.

    The message is written into that queue directly, see 'MessageSubscriptions'.
    """

    _buffer: ESPList[ClientMessage] = field()
    _subscriptions: MessageSubscriptions = field()

    @staticmethod
    def for_communication_protocol(protocol: CommunicationProtocol) -> ClientMessageBuffer:
        return ClientMessageBuffer(
            _buffer=ESPList.default_for_communication_protocol(protocol),
            _subscriptions=MessageSubscriptions.for_communication_protocol(protocol),
        )

    def add(
        self,
        client_id: ClientID,
        message: ESPChannelMessage,
    ) -> None:
        self.add_buffered(ClientMessage(client_id, message))

    def add_buffered(
        self,
        buffered_message: ClientMessage,
    ) -> None:
        """Writes the message into the subscribed queue or, if there is none, stores it in the buffer."""
        queue = self._subscriptions.queue_for(buffered_message.client_id, buffered_message.message.type())
        if queue is None:
            self._debug_log_message(buffered_message, "no subscription is found -> adding to buffer")
            self._buffer.append(buffered_message)
            return
        self._debug_log_message(buffered_message, "subscription was found -> writing into its queue")
        queue.push(buffered_message)

    @staticmethod
    def _debug_log_message(
        buffered_message: ClientMessage,
        description: str,
    ) -> None:
        # This runs for every message in the system, so the debug call is guarded
        if not _message_buffer_logger.is_debug_enabled:
            return
        _message_buffer_logger.debug(
            "CorrelationID: %s  |  Type: %s | client_id: %s: %s",
            buffered_message.message.correlation_id(),
            buffered_message.message.type(),
            buffered_message.client_id,
            description,
        )

    def subscribe(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
    ) -> MessageQueue:
        """Every matching message - including those already buffered - is written into 'queue' until 'unsubscribe'."""
        if len(client_ids) == 0 or len(message_types) == 0:
            raise RuntimeError(
                f"Subscribe on message types {message_types} for client ids {client_ids}: "
                f"NO CLIENT IDS ({len(client_ids)}) OR MESSAGE TYPES ({len(message_types)}). No subscription created.",
            )
        _message_buffer_logger.debug("Subscribe on message types %s for client ids %s", message_types, client_ids)
        queue = self._subscriptions.create_queue_if_not_exists_for(MessageSubscriptionKey(client_ids, message_types))
        if queue is None:
            raise RuntimeError(
                f"Queue already exists for message types {message_types} for client ids {client_ids} -> it is not possible to subscribe again.",
            )
        queue.push_many(self.get_and_delete_of(client_ids, message_types))
        return queue

    def unsubscribe(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
    ) -> None:
        self._subscriptions.remove(MessageSubscriptionKey(client_ids, message_types))

    def get_and_delete_of(
        self,
        client_ids: Tuple[ClientID, ...] = (),
        message_types: Tuple[MessageType, ...] = (),
    ) -> List[ClientMessage]:
        matching_messages: List[ClientMessage]
        with self._buffer.transaction() as messages:
            matching_messages = [
                message
                for message in messages
                if (client_ids and message.client_id in client_ids) and (message_types and message.message.type() in message_types)
            ]
            for message in matching_messages:
                messages.remove(message)
        return matching_messages
