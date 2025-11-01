from __future__ import annotations

from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Callable

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel


@dataclass(frozen=True)
class ESPChannelEndpoint(ABC):

    @abstractmethod
    def listen_async(
        self,
        on_new_channel: Callable[[ConnectionData], None],
    ) -> None:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


@dataclass(frozen=True)
class ConnectionData:
    channel: ESPChannel
    client_address: ConnectionAddress
