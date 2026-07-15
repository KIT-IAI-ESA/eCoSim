from __future__ import annotations

import threading
from dataclasses import dataclass, field

from ecosim_common.config.client_id import ClientID
from ecosim_server.data.repositories import Repositories
from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from integration_tests.tech.db.server_time_measurement_repository_in_memory import ServerTimeMeasurementRepositoryInMemory
from integration_tests.tech.db.simulation_state_repository_in_memory import SimulationStateRepositoryInMemory


@dataclass(frozen=True)
class RepositoriesInMemory(Repositories):
    _thread_lock: threading.Lock = field(default_factory=threading.Lock)
    _client_id_to_measurement_repository: dict[ClientID, MeasurementRepositoryInMemory] = field(default_factory=dict)

    simulation_state_repository: SimulationStateRepository = field(default_factory=SimulationStateRepositoryInMemory)
    server_time_measurement_repository: ServerTimeMeasurementRepository = field(
        default_factory=ServerTimeMeasurementRepositoryInMemory,
    )

    def measurement_repository(
        self,
        client_id: ClientID,
    ) -> MeasurementRepositoryInMemory:
        with self._thread_lock:
            if client_id not in self._client_id_to_measurement_repository:
                self._client_id_to_measurement_repository[client_id] = MeasurementRepositoryInMemory()
            return self._client_id_to_measurement_repository[client_id]
