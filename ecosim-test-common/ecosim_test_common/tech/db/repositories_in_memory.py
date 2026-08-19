from __future__ import annotations

from dataclasses import dataclass, field

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.structures.esp_map import ESPMap, ThreadESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.data.repositories import Repositories
from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository
from ecosim_test_common.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from ecosim_test_common.tech.db.server_time_measurement_repository_in_memory import ServerTimeMeasurementRepositoryInMemory
from ecosim_test_common.tech.db.simulation_state_repository_in_memory import SimulationStateRepositoryInMemory


@dataclass(frozen=True)
class RepositoriesInMemory(Repositories):
    _client_id_to_measurement_repository: ESPMap[ClientID, MeasurementRepositoryInMemory] = field(default_factory=lambda: ThreadESPMap())
    simulation_state_repository: SimulationStateRepository = field(default_factory=SimulationStateRepositoryInMemory)
    server_time_measurement_repository: ServerTimeMeasurementRepository = field(
        default_factory=ServerTimeMeasurementRepositoryInMemory,
    )
    _protocol: CommunicationProtocol = field(default=CommunicationProtocol.TCP_SOCKET)

    @staticmethod
    def for_communication_protocol(protocol: CommunicationProtocol) -> "RepositoriesInMemory":
        return RepositoriesInMemory(
            _client_id_to_measurement_repository=ESPMap.of_type(
                map_type=ESPStructureType.THREAD if protocol == CommunicationProtocol.TCP_SOCKET else ESPStructureType.DASK_VARIABLE,
            ),
            simulation_state_repository=SimulationStateRepositoryInMemory.for_communication_protocol(protocol),
            server_time_measurement_repository=ServerTimeMeasurementRepositoryInMemory.for_communication_protocol(protocol),
            _protocol=protocol,
        )

    def measurement_repository(
        self,
        client_id: ClientID,
    ) -> MeasurementRepositoryInMemory:
        with self._client_id_to_measurement_repository.transaction() as client_id_to_measurement:
            if client_id not in client_id_to_measurement:
                client_id_to_measurement[client_id] = MeasurementRepositoryInMemory.for_protocol(self._protocol)
            return client_id_to_measurement[client_id]
