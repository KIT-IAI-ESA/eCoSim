from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
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
    def measurement_repository(
        self,
        client_id: ClientID,
    ) -> MeasurementRepository:
        pass


def create_repositories(
    server_config: ServerConfig,
    simulation_config: SimulationConfig,
) -> "Repositories":
    from ecosim_server.data.repositories_db import RepositoriesDB
    from ecosim_server.data.repositories_file_based import RepositoriesFileBased

    match server_config.database.type:
        case DatabaseType.POSTGRES:
            return RepositoriesDB.create(server_config=server_config, simulation_config=simulation_config)
        case DatabaseType.FILE:
            return RepositoriesFileBased.create(server_config=server_config, simulation_config=simulation_config)
        case _:
            raise Exception(f"Unsupported database type '{server_config.database.type}' for the repositories")
