from __future__ import annotations

import dask.distributed as dd
from typing import override, Callable

from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.dask.simple_dask_message import SimpleDaskMessage
from ecosim_common.communication.dask.esp_dask import ESPDask
from ecosim_common.communication.dask.dask_messages import ReceivedMessage
from ecosim_common.tech.logger.logger import ESPLogger


def _listen_blocking(
                    on_rec: Callable[[ESPChannelMessage], None],
                    dask_client: ESPDask,
) -> None:
    client = dd.get_client()
    finish_channel = dd.Variable("finished_channel", client=client)
    is_finished = finish_channel.get()
    while not is_finished.is_set():
        is_finished = dd.Variable("finished_channel", client=client).get()
        message: ReceivedMessage | None = dask_client.receive()

        if not message:
            is_finished.set()
            DaskChannel._logger.info("Received empty message -> closing connection")

        if (message is not None) and (message.to_esp_channel_message() is not None):
            on_rec(message.to_esp_channel_message())


class DaskChannel(ESPChannel):
    _logger = ESPLogger("DaskChannel")

    def __init__(
        self,
        esp_dask: ESPDask,
    ):
        self._internal_dask_client = esp_dask
        self._is_finished: dd.Event = dd.Event()

    @override
    def close(self) -> None:
        if not self._internal_dask_client.is_connected() or self._is_finished.is_set():
            return
        self._is_finished.set()
        finished = dd.Variable("finished_channel")
        finished.set(self._is_finished)
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
            future = dask_client.submit(_listen_blocking, on_rec=on_message,  dask_client=self._internal_dask_client)
            dd.fire_and_forget(future)

        dask_client.sync(listen_start)
        finished = dd.Variable("finished_channel")
        finished.set(self._is_finished)

    # def _listen(self,
    #             on_message: Callable[[ESPChannelMessage], None],
    #             client_id: ClientID
    #             ) -> None:
    #     while not self._is_finished.is_set():
    #         message = self.listen_blocking()
    #         if message is not None:
    #             on_message(message)

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
        dask_client = dd.get_client()
        message: ReceivedMessage | None = self._internal_dask_client.receive()
        if not message:
            DaskChannel._logger.info("Received empty message -> closing connection")
            self._is_finished.set()
            finish_channel = dd.Variable("finished_channel", client=dask_client)
            finish_channel.set(self._is_finished)
            return None
        # print(message.to_esp_channel_message())
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
            self._internal_dask_client.connect(connection_address=self._internal_dask_client.connection_address())
            self._internal_dask_client.send(
                SimpleDaskMessage.of_esp_channel_message(message=message),
            )
