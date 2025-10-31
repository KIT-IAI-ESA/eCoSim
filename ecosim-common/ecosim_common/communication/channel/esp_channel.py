from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage


@dataclass
class ESPChannel(ABC):

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def listen_async(
        self,
        on_message: Callable[[ESPChannelMessage], None],
    ) -> None:
        pass

    @abstractmethod
    def listen_blocking(
        self,
        timeout_in_seconds: int | None = None,
    ) -> ESPChannelMessage | None:
        pass

    @abstractmethod
    def send(
        self,
        message: ESPChannelMessage,
    ) -> None:
        pass

    @abstractmethod
    def wait_for_finish(self) -> None:
        pass
