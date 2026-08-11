from abc import ABC, abstractmethod
from typing import ClassVar

from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener


class CommunicationLayer(ShutdownListener, ABC):
    _logger: ClassVar[ESPLogger] = ESPLogger("CommunicationLayer")

    def connect(self) -> None:
        if self.is_connected():
            CommunicationLayer._logger.warning(
                "Communication layer is already connected -> do nothing. If you want to reconnect, call 'reconnect()' instead.",
            )
            return
        self._internal_connect()

    def reconnect(
        self,
    ) -> None:
        if not self.is_connected():
            CommunicationLayer._logger.warning("Communication layer is not connected -> the connection will be established.")
        CommunicationLayer._logger.debug("Reconnecting communication layer...")
        self._internal_connect()
        CommunicationLayer._logger.debug("Reconnecting communication layer...done.")

    @abstractmethod
    def _internal_connect(self) -> None:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass
