from __future__ import annotations

from typing import Callable, override

import dask.distributed as dd
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.dask.dask_messages import ReceivedMessage
from ecosim_common.communication.dask.esp_dask import ESPDask
from ecosim_common.communication.dask.simple_dask_message import SimpleDaskMessage
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownManager


class DaskChannel(ESPChannel):
    _logger = ESPLogger("DaskChannel")

    def __init__(
        self,
        esp_dask: ESPDask,
    ):
        self._internal_dask_client = esp_dask
        self._is_finished: dd.Event = dd.Event(name=f"client_finish_{esp_dask.dask_id()}")
        self._is_finished_global: dd.Event = dd.Event(name="global_finish")

    @override
    def close(self) -> None:
        self._is_finished.set()
        connection_address = self._internal_dask_client.connection_address()
        DaskChannel._logger.debug(f"Closing connections to Dask client {connection_address}...")
        self._internal_dask_client.close()
        DaskChannel._logger.info(f"Connection to Dask client {connection_address} closed.")

    @override
    def listen_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        dask_client = dd.get_client()

        async def listen_start() -> None:
            future = dask_client.submit(
                DaskChannel._listen_blocking,
                on_rec=on_message,
                dask_client=self._internal_dask_client,
                event_name=f"client_finish_{self._internal_dask_client.dask_id()}",
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
        dd.get_client()
        message: ReceivedMessage | None = self._internal_dask_client.receive()
        if not message:
            DaskChannel._logger.info("Received empty message -> closing connection")
            self._is_finished.set()
            return None
        return message.to_esp_channel_message()

    @override
    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        if not self._internal_dask_client.is_connected():
            raise Exception("Dask client already closed")
        try:
            self._internal_dask_client.send(
                SimpleDaskMessage.of_esp_channel_message(message=message),
            )
        except Exception as e:
            DaskChannel._logger.debug(
                f"Send messsage to server failed - recreating dask client connection and try again. Error: {e}",
            )
            self._internal_dask_client.connect()
            self._internal_dask_client.send(
                SimpleDaskMessage.of_esp_channel_message(message=message),
            )

    # Needs to be a static method due to serialization issues when submitting via dd_client.submit().
    # A non-static method would have either the cls or self as the first parameter.
    # In addition, dask.distribute.client.Client.submit expects pure functions by default -> so it makes
    # sense to make it static in any case.
    @staticmethod
    def _listen_blocking(
        on_rec: Callable[[ESPChannelMessage], None],
        dask_client: ESPDask,
        event_name: str,
    ) -> None:
        dd_client = dd.get_client()
        is_finished = dd.Event(name=event_name)
        is_finished_global = dd.Event(name="global_finish")
        dd.secede()  # since it is a long-lived task, we need to secede it from the common thread pool to not block other tasks
        while not is_finished.is_set() and not is_finished_global.is_set():
            message: ReceivedMessage | None = dask_client.receive()

            if not message:
                is_finished.set()
                is_finished_global.set()
                DaskChannel._logger.info("Received empty message -> closing connection")

            if (message is not None) and (message.to_esp_channel_message() is not None):
                try:
                    on_rec(message.to_esp_channel_message())
                except Exception as e:
                    is_finished.set()
                    is_finished_global.set()
                    DaskChannel._logger.error(f"Error when processing message: {e}")
                    dd_client.run(ShutdownManager().set_dask_shutdown)
                    raise e
