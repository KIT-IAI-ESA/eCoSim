from abc import ABC, abstractmethod
from dataclasses import dataclass

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel


@dataclass(frozen=True)
class ESPChannelConnector(ABC):

    @abstractmethod
    def connect(
        self,
        connection_address: ConnectionAddress,
        timeout_in_seconds: int = 30,
    ) -> ESPChannel:
        pass
