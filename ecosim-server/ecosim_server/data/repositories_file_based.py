from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.measurement_repository_file import MeasurementRepositoryFile
from ecosim_server.simulation.state.simulation_state_repository_file import SimulationStateRepositoryFile
from ecosim_server.tech.db.server_time_measurement_repository_file import ServerTimeMeasurementRepositoryFile


@dataclass(frozen=True)
class RepositoriesFileBased(Repositories):
    simulation_state_repository: SimulationStateRepositoryFile = field()
    server_time_measurement_repository: ServerTimeMeasurementRepositoryFile = field()
    _directory: Path = field()
    _communication_protocol: CommunicationProtocol = field()
    _measurement_repository_creation_lock: ParallelLock = field()
    _client_id_to_measurement_repository: dict[ClientID, MeasurementRepositoryFile] = field(default_factory=dict)

    @staticmethod
    def create(
        server_config: ServerConfig,
    ) -> RepositoriesFileBased:
        directory = server_config.database.directory
        communication_protocol = server_config.server.communication_protocol
        return RepositoriesFileBased(
            _directory=directory,
            _communication_protocol=communication_protocol,
            _measurement_repository_creation_lock=ParallelLock.for_protocol(communication_protocol),
            simulation_state_repository=SimulationStateRepositoryFile.create(
                directory=directory,
                communication_protocol=communication_protocol,
            ),
            server_time_measurement_repository=ServerTimeMeasurementRepositoryFile.create(
                directory=directory,
                communication_protocol=communication_protocol,
            ),
        )

    @override
    def measurement_repository(
        self,
        client_id: ClientID,
    ) -> MeasurementRepositoryFile:
        if client_id in self._client_id_to_measurement_repository:
            return self._client_id_to_measurement_repository[client_id]
        if client_id not in self._client_id_to_measurement_repository:
            with self._measurement_repository_creation_lock:
                if client_id not in self._client_id_to_measurement_repository:
                    self._client_id_to_measurement_repository[client_id] = MeasurementRepositoryFile.create(
                        directory=self._directory,
                        simulator_name=client_id.simulator_name,
                        communication_protocol=self._communication_protocol,
                    )
        return self._client_id_to_measurement_repository[client_id]
