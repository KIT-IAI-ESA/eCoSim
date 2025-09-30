from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.config.client_id import ClientID
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository


@dataclass(frozen=True)
class Repositories(ABC):
    _logger: ClassVar[ESPLogger] = ESPLogger("Repositories")

    simulation_state_repository: SimulationStateRepository
    server_time_measurement_repository: ServerTimeMeasurementRepository

    @abstractmethod
    def measurement_repository(self,
                               client_id: ClientID
                               ) -> MeasurementRepository:
        pass
