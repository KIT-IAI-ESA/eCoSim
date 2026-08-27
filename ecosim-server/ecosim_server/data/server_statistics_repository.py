from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import ClassVar

from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType


class ServerTimeMeasurementRepository(ABC):
    _logger: ClassVar[ESPLogger] = ESPLogger("ServerTimeMeasurementRepository")

    @abstractmethod
    def put(
        self,
        server_time_measurement: ServerTimeMeasurement,
    ) -> None:
        pass

    @abstractmethod
    def get_start(
        self,
        type: ServerTimeMeasurementType,
    ) -> datetime | None:
        pass

    @abstractmethod
    def get_end(
        self,
        type: ServerTimeMeasurementType,
    ) -> datetime | None:
        pass

    def get_time(
        self,
        type: ServerTimeMeasurementType,
    ) -> timedelta | None:
        start = self.get_start(type)
        if start is None:
            ServerTimeMeasurementRepository._logger.warning("get_time: No start time found for type: %s", type)
            return None
        end = self.get_start(type)
        if end is None:
            ServerTimeMeasurementRepository._logger.warning("get_time: No end time found for type: %s", type)
            return None
        return end - start
