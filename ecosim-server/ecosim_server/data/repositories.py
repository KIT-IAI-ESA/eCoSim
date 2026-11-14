from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from ecosim_common.config.database_type import DatabaseType
from sqlalchemy.exc import OperationalError
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
            try:
                return RepositoriesDB.create(server_config=server_config, simulation_config=simulation_config)
            except OperationalError as error:
                raise ConnectionError(
                    f"Cannot use PostgreSQL at {server_config.database.server_location()}: {str(error.orig).splitlines()[0]}. "
                    + "To write the results as files instead, pass --database-type file",
                ) from error
        case DatabaseType.FILE:
            return RepositoriesFileBased.create(server_config=server_config, simulation_config=simulation_config)
        case _:
            raise Exception(f"Unsupported database type '{server_config.database.type}' for the repositories")
