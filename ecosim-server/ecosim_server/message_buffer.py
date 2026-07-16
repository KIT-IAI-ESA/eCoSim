from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, List, Set, Tuple, Type, override

import dask.distributed as dd
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.message_data import MESSAGE_DATA
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_lock import ParallelLock

_message_buffer_logger = ESPLogger("MessageBuffer")


@dataclass
class ClientMessageBuffer:
    _buffer: List[BufferedClientMessage] = field()
    _buffer_lock: ParallelLock = field()
    _callbacks_lock: ParallelLock = field()
    _on_message_callbacks: Set[OnMessageCallbackHandler] = field()
    _communication_protocol: CommunicationProtocol = field()  # TODO_OSR: low prio: search for alternatives to the 'protocol' field

    @staticmethod
    def for_communication_protocol(protocol: CommunicationProtocol) -> ClientMessageBuffer:
        return ClientMessageBuffer(
            _buffer=[],
            _buffer_lock=ParallelLock.for_protocol(protocol),
            _callbacks_lock=ParallelLock.for_protocol(protocol),
            _on_message_callbacks=set(),
            _communication_protocol=protocol,
        )

    def add(
        self,
        client_id: ClientID,
        message: ESPChannelMessage,
    ) -> None:
        _message_buffer_logger.debug(
            f"Adding new message to buffer. CorrelationID: {message.correlation_id()}  |  Type: {message.type()} | client_id: {client_id}",
        )
        buffered_message = BufferedClientMessage(client_id, message)
        with self._callbacks_lock:
            callback = self._find_on_message_callback(buffered_message)
        if callback is not None:
            callback.execute_async(buffered_message)
            return

        with self._buffer_lock:
            self._buffer.append(buffered_message)

    def _find_on_message_callback(
        self,
        message: BufferedClientMessage,
    ) -> OnMessageCallbackHandler | None:
        for callback in self._on_message_callbacks.copy():
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
            return
        message_callback: OnMessageCallbackHandler = OnMessageCallbackHandler.for_communication_protocol(
            protocol=self._communication_protocol,
            client_ids=client_ids,
            message_types=message_types,
            callback=callback,
        )
        with self._callbacks_lock:
            if message_callback in self._on_message_callbacks:
                _message_buffer_logger.warning(
                    f"You can only listen once on the given parameters: {client_ids} | {message_types}. The new callback is discarded.",
                )
                return
            self._on_message_callbacks.add(message_callback)
            matching_messages = self._get_and_delete_internal(client_ids, message_types)
        for message in matching_messages:
            message_callback.execute_async(message)

    def remove_on_message_callback(
        self,
        client_ids: Tuple[ClientID, ...],
        message_types: Tuple[MessageType, ...],
    ) -> None:
        with self._callbacks_lock:
            self._on_message_callbacks.remove(
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
        with self._buffer_lock:
            return self._get_and_delete_internal(client_ids, message_types)

    def _get_and_delete_internal(
        self,
        client_ids: Tuple[ClientID, ...] = (),
        message_types: Tuple[MessageType, ...] = (),
    ) -> List[BufferedClientMessage]:
        matching_messages = [
            message
            for message in self._buffer
            if (client_ids and message.client_id in client_ids) and (message_types and message.message.type() in message_types)
        ]
        for message in matching_messages:
            self._buffer.remove(message)
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
        _message_buffer_logger.debug(f"Executing (threading) callback for {message.client_id} on {message.message.type()}")
        threading.Thread(target=self.callback, args=[message]).start()


@dataclass(frozen=True, eq=False)
class OnMessageCallbackHandlerDask(OnMessageCallbackHandler):
    @override
    def execute_async(
        self,
        message: BufferedClientMessage,
    ) -> None:
        _message_buffer_logger.debug(f"Executing (dask) callback for {message.client_id} on {message.message.type()}")
        dask_client = dd.get_client()

        async def f() -> None:
            future = dask_client.submit(self.callback, message)
            dd.fire_and_forget(future)

        dask_client.sync(f)
