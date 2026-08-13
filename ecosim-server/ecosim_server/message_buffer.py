from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, List, Tuple, Type, override

import dask.distributed as dd
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.message_data import MESSAGE_DATA
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.structures.esp_list import ESPList
from ecosim_common.tech.structures.esp_set import ESPSet
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType

_message_buffer_logger = ESPLogger("MessageBuffer")


@dataclass
class ClientMessageBuffer:
    _buffer: ESPList[BufferedClientMessage] = field()
    # TODO_OSR: this is only a set -> checking for existing callbacks is error prone
    _on_message_callbacks: ESPSet[OnMessageCallbackHandler] = field()
    _communication_protocol: CommunicationProtocol = field()  # TODO_OSR: low prio: search for alternatives to the 'protocol' field

    @staticmethod
    def for_communication_protocol(protocol: CommunicationProtocol) -> ClientMessageBuffer:
        return ClientMessageBuffer(
            _buffer=ESPList.of_type(
                list_type=ESPStructureType.DASK_VARIABLE if protocol == CommunicationProtocol.DASK else ESPStructureType.THREAD,
            ),
            _on_message_callbacks=ESPSet.of_type(
                set_type=ESPStructureType.DASK_VARIABLE if protocol == CommunicationProtocol.DASK else ESPStructureType.THREAD,
                dask_name="message_buffer_on_message_callbacks",
            ),
            _communication_protocol=protocol,
        )

    def add(
        self,
        client_id: ClientID,
        message: ESPChannelMessage,
    ) -> None:
        # This runs for every message in the system, so the debug calls below are guarded
        if _message_buffer_logger.is_debug_enabled:
            _message_buffer_logger.debug(
                "Adding new message to buffer. CorrelationID: %s  |  Type: %s | client_id: %s",
                message.correlation_id(),
                message.type(),
                client_id,
            )
        buffered_message = BufferedClientMessage(client_id, message)
        callback = self._find_on_message_callback(buffered_message)
        if callback is not None:
            if _message_buffer_logger.is_debug_enabled:
                _message_buffer_logger.debug(
                    "CorrelationID: %s  |  Type: %s | client_id: %s: executing callback...",
                    message.correlation_id(),
                    message.type(),
                    client_id,
                )
            callback.execute_async(buffered_message)
            return
        if _message_buffer_logger.is_debug_enabled:
            _message_buffer_logger.debug(
                "CorrelationID: %s  |  Type: %s | client_id: %s: no callback is found -> adding to buffer",
                message.correlation_id(),
                message.type(),
                client_id,
            )
        self._buffer.append(buffered_message)

    def _find_on_message_callback(
        self,
        message: BufferedClientMessage,
    ) -> OnMessageCallbackHandler | None:
        callbacks = self._on_message_callbacks.get_snapshot()
        for callback in callbacks:
            if message.client_id in callback.client_ids and message.message.type() in callback.message_types:
                return callback
        return None

    def on_message(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
        callback: Callable[[BufferedClientMessage], None],
    ) -> None:
        if len(client_ids) == 0 or len(message_types) == 0:
            _message_buffer_logger.warning(
                "Register on_message %s for client_ids %s: NO CLIENT IDS (f%s) OR MESSAGE TYPES (%s).",
                message_types,
                client_ids,
                len(client_ids),
                len(message_types),
            )
            return
        _message_buffer_logger.debug("Register callback on message types %s for client ids %s", message_types, client_ids)
        message_callback: OnMessageCallbackHandler = OnMessageCallbackHandler.for_communication_protocol(
            protocol=self._communication_protocol,
            client_ids=client_ids,
            message_types=message_types,
            callback=callback,
        )
        with self._on_message_callbacks.transaction() as callbacks:
            if message_callback in callbacks:
                _message_buffer_logger.warning(
                    "You can only listen once on the given parameters: %s | %s. The new callback is discarded.",
                    client_ids,
                    message_types,
                )
                return
            callbacks.add(message_callback)
        matching_messages = self.get_and_delete_of(client_ids, message_types)
        for message in matching_messages:
            if _message_buffer_logger.is_debug_enabled:
                _message_buffer_logger.debug(
                    "Message found for newly registered callback on message types %s for client ids %s: type: '%s'",
                    message_types,
                    client_ids,
                    message.message.type(),
                )
            message_callback.execute_async(message)

    def remove_on_message_callback(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
    ) -> None:
        with self._on_message_callbacks.transaction() as callbacks:
            callbacks.remove(
                OnMessageCallbackHandler.for_communication_protocol(
                    protocol=self._communication_protocol,
                    client_ids=client_ids,
                    message_types=message_types,
                    callback=lambda m: None,
                ),
            )

    def get_and_delete_of(
        self,
        client_ids: Tuple[ClientID, ...] = (),
        message_types: Tuple[MessageType, ...] = (),
    ) -> List[BufferedClientMessage]:
        matching_messages: List[BufferedClientMessage]
        with self._buffer.transaction() as messages:
            matching_messages = [
                message
                for message in messages
                if (client_ids and message.client_id in client_ids) and (message_types and message.message.type() in message_types)
            ]
            for message in matching_messages:
                messages.remove(message)
        return matching_messages


class BufferedClientMessage:
    def __init__(
        self,
        client_id: ClientID,
        message: ESPChannelMessage,
    ):
        self.time_stamp_ns = time.time_ns()
        self.client_id = client_id
        self.message = message

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        return (
            isinstance(other, BufferedClientMessage)
            and self.time_stamp_ns == other.time_stamp_ns
            and self.client_id == other.client_id
            and self.message.type() == other.message.type()
            and self.message.correlation_id() == other.message.correlation_id()
            and self.message.payload() == other.message.payload()
        )

    def __hash__(self) -> int:
        return hash(
            (
                self.time_stamp_ns,
                self.client_id,
                self.message.type(),
                self.message.correlation_id(),
                self.message.payload(),
            ),
        )

    def payload(
        self,
        clazz: Type[MESSAGE_DATA],
    ) -> MESSAGE_DATA:
        return self.message.payload(clazz)


@dataclass(frozen=True, eq=False)
class OnMessageCallbackHandler(ABC):
    client_ids: Tuple[ClientID, ...]
    message_types: Tuple[MessageType, ...]
    callback: Callable[[BufferedClientMessage], None]

    @abstractmethod
    def execute_async(
        self,
        message: BufferedClientMessage,
    ) -> None:
        pass

    @staticmethod
    def for_communication_protocol(
        protocol: CommunicationProtocol,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
        callback: Callable[[BufferedClientMessage], None],
    ) -> OnMessageCallbackHandler:
        match protocol:
            case CommunicationProtocol.DASK:
                return OnMessageCallbackHandlerDask(
                    client_ids=client_ids,
                    message_types=message_types,
                    callback=callback,
                )
            case _:
                return OnMessageCallbackHandlerThreading(
                    client_ids=client_ids,
                    message_types=message_types,
                    callback=callback,
                )

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        if not isinstance(other, OnMessageCallbackHandler):
            return False
        return self.__hash__() == other.__hash__()

    def __hash__(self) -> int:
        return hash((self.client_ids, self.message_types))


@dataclass(frozen=True, eq=False)
class OnMessageCallbackHandlerThreading(OnMessageCallbackHandler):
    @override
    def execute_async(
        self,
        message: BufferedClientMessage,
    ) -> None:
        if _message_buffer_logger.is_debug_enabled:
            _message_buffer_logger.debug("Executing (threading) callback for %s on %s", message.client_id, message.message.type())
        threading.Thread(target=self.callback, args=[message]).start()


@dataclass(frozen=True, eq=False)
class OnMessageCallbackHandlerDask(OnMessageCallbackHandler):
    @override
    def execute_async(
        self,
        message: BufferedClientMessage,
    ) -> None:
        if _message_buffer_logger.is_debug_enabled:
            _message_buffer_logger.debug("Executing (dask) callback for %s on %s", message.client_id, message.message.type())
        dask_client = dd.get_client()

        async def f() -> None:
            future = dask_client.submit(self.callback, message)
            dd.fire_and_forget(future)

        dask_client.sync(f)
