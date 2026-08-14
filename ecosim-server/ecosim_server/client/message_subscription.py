from __future__ import annotations

from dataclasses import dataclass, field
from types import TracebackType
from typing import List, Tuple

from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_server.client.client_message import ClientMessage
from ecosim_server.client.client_message_buffer import ClientMessageBuffer


@dataclass
class MessageSubscription:
    """
    A live subscription on the 'ClientMessageBuffer' that queues every matching message until it is closed.
    Messages that are still queued when the subscription is closed are handed back to the message buffer.
    """

    _message_buffer: ClientMessageBuffer = field()
    _client_ids: Tuple[ClientID, ...] = field()
    _message_types: Tuple[MessageType, ...] = field()
    _queue: ESPQueue[ClientMessage] = field()

    @staticmethod
    def open(
        message_buffer: ClientMessageBuffer,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
    ) -> MessageSubscription:
        queue = message_buffer.subscribe(client_ids, message_types)
        return MessageSubscription(
            _message_buffer=message_buffer,
            _client_ids=client_ids,
            _message_types=message_types,
            _queue=queue,
        )

    def next_message(
        self,
        timeout_in_seconds: float | None = None,
    ) -> ClientMessage | None:
        return self._queue.pop_or_none(timeout=timeout_in_seconds)

    def pending_messages(self) -> List[ClientMessage]:
        """Returns every message that is already queued, without waiting for more."""
        return self._queue.pop_all()

    def pending_message_count(self) -> int:
        return self._queue.qsize()

    def close(self) -> None:
        self._message_buffer.unsubscribe(self._client_ids, self._message_types)
        for message in self._queue.pop_all():
            self._message_buffer.add_buffered(message)

    def __enter__(self) -> MessageSubscription:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
