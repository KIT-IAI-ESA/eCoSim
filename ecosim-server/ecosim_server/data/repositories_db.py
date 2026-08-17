from __future__ import annotations

from dataclasses import dataclass, field
from typing import override

from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_server.measurement.measurement_repository_db import MeasurementRepositoryDB
from ecosim_server.measurement.simulation_state_repository_db import SimulationStateRepositoryDB
from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_tech_abstract import DbTechAbstract
from ecosim_server.tech.db.postgres_tech import PostgresTech
from ecosim_server.tech.db.server_time_measurement_repository_db import ServerTimeMeasurementRepositoryDB


@dataclass(frozen=True)
class RepositoriesDB(Repositories):
    _simulation_config: SimulationConfig = field()
    _db_connection: DBConnection = field()
    _measurement_repository_creation_lock: ParallelLock = field()
    _client_id_to_measurement_repository: dict[ClientID, MeasurementRepository] = field(default_factory=dict)

    @staticmethod
    def create(server_config: ServerConfig, simulation_config: SimulationConfig) -> RepositoriesDB:
        db_tech = RepositoriesDB._get_db_tech(server_config)
        db_tech.init_db()
        db_connection = db_tech.db_connection()
        return RepositoriesDB(
            _simulation_config=simulation_config,
            _db_connection=db_connection,
            _measurement_repository_creation_lock=ParallelLock.for_protocol(server_config.server.communication_protocol),
            simulation_state_repository=SimulationStateRepositoryDB(
                _db_connection=db_connection,
                _write_lock=ParallelLock.for_protocol(
                    server_config.server.communication_protocol,
                ),
            ),
            server_time_measurement_repository=ServerTimeMeasurementRepositoryDB(db_connection=db_connection),
        )

    @override
    def measurement_repository(
        self,
        client_id: ClientID,
    ) -> MeasurementRepository:
        if client_id in self._client_id_to_measurement_repository:
            return self._client_id_to_measurement_repository[client_id]
        with self._measurement_repository_creation_lock:
            if client_id not in self._client_id_to_measurement_repository:
                self._client_id_to_measurement_repository[client_id] = MeasurementRepositoryDB(
                    simulation_config=self._simulation_config,
                    client_id=client_id,
                    db_connection=self._db_connection,
                )
        return self._client_id_to_measurement_repository[client_id]

    @staticmethod
    def _get_db_tech(
        server_config: ServerConfig,
    ) -> DbTechAbstract:
        match server_config.database.type:
            case "postgres":
                return PostgresTech(server_config)
            case _:
                raise Exception(f"Unsupported database type '{server_config.database.type}'")
