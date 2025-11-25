import time
from dataclasses import dataclass

from typing_extensions import override

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.communication.dask.esp_dask import ESPDask
from ecosim_common.tech.logger.logger import ESPLogger


@dataclass(frozen=True)
class DaskConnector(ESPChannelConnector):
    _logger = ESPLogger("DaskConnector")

    @override
    def connect(
        self,
        connection_address: ConnectionAddress,
        timeout_in_seconds: int = 30,
    ) -> ESPChannel:
        start_time = time.time()
        esp_dask = ESPDask()
        connected: bool = False
        while not connected and (time.time() - start_time) < timeout_in_seconds:
            try:
                esp_dask.connect(connection_address)
                connected = True
            except Exception as e:
                DaskConnector._logger.warning(
                    f"Cannot connect to Dask client - trying in sum for {timeout_in_seconds}s. Error: {e}",
                )
                time.sleep(1)

        if not connected:
            raise ConnectionError(f"Could not connect to Dask client {connection_address}")
        DaskConnector._logger.info(f"Connected to Dask client successfully: {connection_address}")
        return DaskChannel(esp_dask)
