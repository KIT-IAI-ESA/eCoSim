from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


@dataclass(kw_only=True)
class ESPChannel(ABC):
    @abstractmethod
    def close(self) -> None:
        pass

    # TODO_OSR: think about returning an ESPQueue
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
        """
        :return ESPChannelMessage | None: The received message or None if the connection was closed.
        """
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

    @abstractmethod
    def is_listening_event(self) -> ParallelEvent:
        pass
