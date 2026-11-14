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
        failed_attempts = 0
        while not connected and (time.time() - start_time) < timeout_in_seconds:
            try:
                channel.connect()
                connected = channel.is_connected()
            except Exception as e:
                failed_attempts += 1
                self._log_failed_attempt(
                    connection_address=connection_address,
                    failed_attempts=failed_attempts,
                    error=e,
                    timeout_in_seconds=timeout_in_seconds,
                )
                time.sleep(1)

        if not connected:
            raise ConnectionError(f"Could not connect to {connection_address} via {transport}")
        ESPChannelConnector._logger.info("Connected to the server at %s via %s", connection_address, transport)
        return channel

    def _log_failed_attempt(self, connection_address: ConnectionAddress, failed_attempts: int, error: Exception, timeout_in_seconds: int) -> None:
        transport = self._communication_protocol.serialized
        # a client that starts before the server listens is normal, so the retries are no warning
        if failed_attempts == 1:
            ESPChannelConnector._logger.info(
                "Cannot connect to the server at %s via %s yet (%s), trying again for up to %s s",
                connection_address,
                transport,
                error,
                timeout_in_seconds,
            )
        ESPChannelConnector._logger.debug("Attempt %s to connect to %s via %s failed: %s", failed_attempts, connection_address, transport, error)

    def listener(
        self,
        connection_address: ConnectionAddress,
    ) -> ESPChannel:
        return ESPChannel.for_protocol(self._communication_protocol, connection_address)
