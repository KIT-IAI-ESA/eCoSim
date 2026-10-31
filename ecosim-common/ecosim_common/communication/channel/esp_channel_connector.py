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
        transport = self._communication_protocol.serialized
        channel: ESPChannel = ESPChannel.for_protocol(self._communication_protocol, connection_address)
        while not connected and (time.time() - start_time) < timeout_in_seconds:
            try:
                channel.connect()
                connected = channel.is_connected()
            except Exception as e:
                ESPChannelConnector._logger.warning(
                    "Cannot connect to %s via %s - trying in sum for %ss. Error: %s",
                    connection_address,
                    transport,
                    timeout_in_seconds,
                    e,
                )
                time.sleep(1)

        if not connected:
            raise ConnectionError(f"Could not connect to {connection_address} via {transport}")
        ESPChannelConnector._logger.info("Connected to %s via %s successfully.", connection_address, transport)
        return channel

    def listener(
        self,
        connection_address: ConnectionAddress,
    ) -> ESPChannel:
        return ESPChannel.for_protocol(self._communication_protocol, connection_address)
