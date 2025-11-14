from __future__ import annotations
import threading
from dataclasses import dataclass, field

from ecosim_server.config.server_config import ServerConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.tech.db.ServerTimeMeasurementRepositoryDB import ServerTimeMeasurementRepositoryDB
from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_tech_abstract import DbTechAbstract
from ecosim_server.tech.db.postgres_tech import PostgresTech
from ecosim_server.tech.db.simdb.MeasurementRepositoryDB import MeasurementRepositoryDB
from ecosim_server.tech.db.simdb.SimulationStateRepositoryDB import SimulationStateRepositoryDB


@dataclass(frozen=True)
class RepositoriesDB(Repositories):
    _simulation_config: SimulationConfig = field()
    _db_connection: DBConnection = field()
    _thread_lock: threading.Lock = field(default_factory=threading.Lock)
    _client_id_to_measurement_repository: dict[ClientID, MeasurementRepository] = field(default_factory=dict)

    @staticmethod
    def create(server_config: ServerConfig, simulation_config: SimulationConfig) -> RepositoriesDB:
        db_tech = RepositoriesDB._get_db_tech(server_config)
        db_tech.init_db()
        db_connection = db_tech.db_connection()
        return RepositoriesDB(
            _simulation_config=simulation_config,
            _db_connection=db_connection,
            simulation_state_repository=SimulationStateRepositoryDB(db_connection=db_connection),
            server_time_measurement_repository=ServerTimeMeasurementRepositoryDB(db_connection=db_connection),
        )

    def measurement_repository(
        self,
        client_id: ClientID,
    ) -> MeasurementRepository:
        with self._thread_lock:
            if client_id not in self._client_id_to_measurement_repository:
                self._client_id_to_measurement_repository[client_id] = MeasurementRepositoryDB(
                    self._simulation_config, client_id, self._db_connection,
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
