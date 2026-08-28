from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import ClassVar

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.logger import ESPLogger


@dataclass(frozen=True)
class ESPChannelConnector:
    _logger: ClassVar[ESPLogger] = ESPLogger("ESPChannelConnector")

    _communication_protocol: CommunicationProtocol = field()

    def connect(
        self,
        connection_address: ConnectionAddress,
        timeout_in_seconds: int = 30,
    ) -> ESPChannel:
        start_time = time.time()
        connected: bool = False
        channel: ESPChannel = ESPChannel.for_protocol(self._communication_protocol, connection_address)
        while not connected and (time.time() - start_time) < timeout_in_seconds:
            try:
                channel.connect()
                connected = channel.is_connected()
            except Exception as e:
                ESPChannelConnector._logger.warning("Cannot connect to Dask client - trying in sum for %ss. Error: %s", timeout_in_seconds, e)
                time.sleep(1)

        if not connected:
            raise ConnectionError(f"Could not connect to Dask client {connection_address}")
        ESPChannelConnector._logger.info("Connected to Dask client successfully: %s", connection_address)
        return channel

    def listener(
        self,
        connection_address: ConnectionAddress,
    ) -> ESPChannel:
        return ESPChannel.for_protocol(self._communication_protocol, connection_address)
