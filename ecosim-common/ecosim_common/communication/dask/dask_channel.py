from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, override

import dask.distributed as dd
from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.binary_message.simple_binary_message import SimpleBinaryMessage
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.dask.esp_dask import ESPDask
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


@dataclass
class DaskChannel(ESPChannel):
    _logger = ESPLogger("DaskChannel")

    _internal_dask_client: ESPDask = field()
    _is_finished: ParallelEvent = field(default_factory=lambda: ParallelEvent.dask())

    @override
    def close(self) -> None:
        self._is_finished.set()
        # self.send("empty")  # type: ignore[arg-type] # TODO_AFTER_MERGE: this was added
        connection_address = self._internal_dask_client.connection_address()
        DaskChannel._logger.debug(f"Closing connections to Dask client {connection_address}...")
        self._internal_dask_client.close()  # TODO_AFTER_MERGE: this was commented out
        DaskChannel._logger.info(f"Connection to Dask client {connection_address} closed.")

    @override
    def listen_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        dask_client = dd.get_client()

        async def listen_start() -> None:
            future = dask_client.submit(
                DaskChannel._listen_async_internal,
                on_message=on_message,
                dask_client=self._internal_dask_client,
                is_finished_event=self._is_finished,
                pure=False,
            )
            dd.fire_and_forget(future)

        dask_client.sync(listen_start)

    @override
    def wait_for_finish(
        self,
        timeout_in_seconds: int | None = None,
    ) -> None:
        self._is_finished.wait(timeout_in_seconds)

    @override
    def listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        return DaskChannel._listen_blocking_internal(
            dask_client=self._internal_dask_client,
            is_finished_event=self._is_finished,
        )

    @staticmethod
    def _listen_blocking_internal(
        dask_client: ESPDask,
        is_finished_event: ParallelEvent,
    ) -> ESPChannelMessage | None:
        message: ReceivedBinaryMessage | None = dask_client.receive()
        if not message:
            DaskChannel._logger.info("Received empty message -> closing connection")
            is_finished_event.set()
            return None
        return message.to_esp_channel_message()

    @override
    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        # TODO_AFTER_MERGE: newly added 'not self._is_finished.is_set()'
        if not self._internal_dask_client.is_connected() and not self._is_finished.is_set():
            raise Exception("Dask client already closed")
        try:
            self._internal_dask_client.send(
                SimpleBinaryMessage.of_esp_channel_message(message=message),
            )
        except Exception as e:
            # TODO_AFTER_MERGE: reconnecting is not specified in the abstraction -> either specify or refactor
            DaskChannel._logger.debug(
                f"Send messsage to server failed - recreating dask client connection and try again. Error: {e}",
            )
            # TODO_AFTER_MERGE: this was commented out -> handle this
            # self._internal_dask_client.connect()
            # self._internal_dask_client.send(
            #     SimpleBinaryMessage.of_esp_channel_message(message=message),
            # )

    # Needs to be a static method due to serialization issues when submitting via dd_client.submit().
    # A non-static method would have either the cls or self as the first parameter.
    # In addition, dask.distribute.client.Client.submit expects pure functions by default -> so it makes
    # sense to make it static in any case.
    @staticmethod
    def _listen_async_internal(
        on_message: Callable[[ESPChannelMessage], None],
        dask_client: ESPDask,
        is_finished_event: ParallelEvent,
    ) -> None:
        dd.secede()  # since it is a long-lived task, we need to secede it from the common thread pool to not block other tasks
        while not is_finished_event.is_set():
            message: ESPChannelMessage | None = DaskChannel._listen_blocking_internal(
                dask_client=dask_client,
                is_finished_event=is_finished_event,
            )
            if message is not None:
                on_message(message)
