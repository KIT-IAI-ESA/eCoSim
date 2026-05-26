from __future__ import annotations
import threading
import dask.distributed as dd
import time
from dataclasses import dataclass
from typing import List, Tuple, Set, Callable, Type, Any

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.message_data import MESSAGE_DATA
from ecosim_common.communication.message_type import MessageType
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.config.client_id import ClientID


class ClientMessageBuffer:
    _logger = ESPLogger("MessageBuffer")

    def __init__(self) -> None:
        self._buffer: List[BufferedClientMessage] = []
        try:  # use dask.Lock if using dask
            dd.get_client()
            self._buffer_lock: threading.Lock | dd.Lock = dd.Lock()
            self._callbacks_lock: threading.Lock | dd.Lock = dd.Lock()
        except ValueError:  # otherwise normal threading.Lock
            self._buffer_lock = threading.Lock()
            self._callbacks_lock = threading.Lock()

        self._on_message_callbacks: Set[OnMessageCallbackHandler | OnMessageCallbackHandlerDask] = set()

    def add(
        self,
        client_id: ClientID,
        message: ESPChannelMessage,
    ) -> None:
        ClientMessageBuffer._logger.debug(
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
    ) -> OnMessageCallbackHandler | OnMessageCallbackHandlerDask | None:
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
        message_callback: OnMessageCallbackHandler | OnMessageCallbackHandlerDask
        if len(client_ids) == 0 or len(message_types) == 0:
            return
        if type(self._buffer_lock) is dd.lock.Lock:
            message_callback = OnMessageCallbackHandlerDask(client_ids, message_types, callback)
        else:
            message_callback = OnMessageCallbackHandler(client_ids, message_types, callback)
        with self._callbacks_lock:
            if message_callback in self._on_message_callbacks:
                ClientMessageBuffer._logger.warning(
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
        if type(self._callbacks_lock) is dd.lock.Lock:
            with self._callbacks_lock:
                self._on_message_callbacks = {
                    call for call in self._on_message_callbacks.copy()
                    if call.__hash__() != client_ids.__hash__() + message_types.__hash__()
                }
        else:
            with self._callbacks_lock:
                self._on_message_callbacks.remove(OnMessageCallbackHandler(client_ids, message_types, lambda m: None))

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
            message for message in self._buffer if
            (client_ids and message.client_id in client_ids) and
            (message_types and message.message.type() in message_types)
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
            isinstance(other, BufferedClientMessage) and
            self.time_stamp_ns == other.time_stamp_ns and
            self.client_id == other.client_id and
            self.message.type() == other.message.type() and
            self.message.correlation_id() == other.message.correlation_id() and
            self.message.payload() == other.message.payload()
        )

    def __hash__(self) -> int:
        return hash((
            self.time_stamp_ns, self.client_id, self.message.type(), self.message.correlation_id(),
            self.message.payload(),
        ))

    def payload(
        self,
        clazz: Type[MESSAGE_DATA],
    ) -> MESSAGE_DATA:
        return self.message.payload(clazz)


@dataclass(frozen=True)
class OnMessageCallbackHandler:
    client_ids: Tuple[ClientID, ...]
    message_types: Tuple[MessageType, ...]
    callback: Callable[[BufferedClientMessage], None]

    def execute_async(
        self,
        message: BufferedClientMessage,
    ) -> None:
        threading.Thread(target=self.callback, args=[message]).start()

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        if not isinstance(other, OnMessageCallbackHandler):
            return False
        return self.__hash__() == other.__hash__()

    def __hash__(self) -> int:
        return self.client_ids.__hash__() + self.message_types.__hash__()


@dataclass(frozen=True)
class OnMessageCallbackHandlerDask:
    client_ids: Tuple[ClientID, ...]
    message_types: Tuple[MessageType, ...]
    callback: Callable[[BufferedClientMessage], None]

    def execute_async(
        self,
        message: BufferedClientMessage,
    ) -> None:
        dask_client = dd.get_client()

        async def f() -> None:
            future = dask_client.submit(self.callback, message)
            dd.fire_and_forget(future)
        dask_client.sync(f)

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        if not isinstance(other, OnMessageCallbackHandler):
            return False
        return self.__hash__() == other.__hash__()

    def __hash__(self) -> int:
        return self.client_ids.__hash__() + self.message_types.__hash__()
