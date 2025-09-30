import threading
from dataclasses import dataclass, field

from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.tech.db.simdb.MeasurementRepositoryDB import MeasurementRepositoryDB


@dataclass(frozen=True)
class RepositoriesDB(Repositories):
    _simulation_config: SimulationConfig = field()
    _thread_lock: threading.Lock = field(default_factory=threading.Lock)
    _client_id_to_measurement_repository: dict[ClientID, MeasurementRepository] = field(default_factory=dict)

    def measurement_repository(self,
                               client_id: ClientID,
                               ) -> MeasurementRepository:
        with self._thread_lock:
            if client_id not in self._client_id_to_measurement_repository:
                self._client_id_to_measurement_repository[client_id] = MeasurementRepositoryDB(
                    self._simulation_config, client_id)
            return self._client_id_to_measurement_repository[client_id]
