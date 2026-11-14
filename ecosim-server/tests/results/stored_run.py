from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_server.measurement.measurement_repository_file import MeasurementRepositoryFile
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository_file import SimulationStateRepositoryFile
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_input, create_output, create_simulator


@dataclass(frozen=True)
class StoredRun:
    """A weather with a temperature and a profile of three values, and a house that gets the temperature, written by the server's repositories."""

    simulation_config_file: Path
    weather: str
    house: str

    @staticmethod
    def in_directory(directory: Path, weather: str = "weather", house: str = "house") -> StoredRun:
        """The PostgreSQL storage defines a table once per process, so a test that writes to it passes names of its own."""
        weather_simulator = create_simulator(weather, create_output("T_out"), create_output("profile"))
        house_simulator = create_simulator(house, create_input("T_out_in", simulator="0", interface="T_out"), create_output("T_room"))
        return StoredRun(simulation_config_file=config_file(directory, weather_simulator, house_simulator), weather=weather, house=house)

    @staticmethod
    def time_of(step: int) -> datetime:
        return datetime(year=2023, month=1, day=1, tzinfo=timezone.utc) + (step + 1) * timedelta(minutes=15)

    def write_files(self, directory: Path, steps: int, state: SimulationState = SimulationState.FINISHED) -> None:
        for simulator_name in (self.weather, self.house):
            repository = StoredRun.file_repository(directory=directory, simulator_name=simulator_name)
            self._write_steps(repository=repository, simulator_name=simulator_name, steps=steps)
        SimulationStateRepositoryFile.create(directory=directory, communication_protocol=CommunicationProtocol.TCP_SOCKET).update(state)

    def write_database(self, server_config: ServerConfig, steps: int) -> None:
        simulation_config = SimulationConfig.of_config_file_and_params(simulation_config_file=self.simulation_config_file, steps=steps)
        repositories = RepositoriesDB.create(server_config=server_config, simulation_config=simulation_config)
        for client_id in simulation_config.client_ids():
            repository = repositories.measurement_repository(client_id=client_id)
            self._write_steps(repository=repository, simulator_name=client_id.simulator_name, steps=steps)
        repositories.simulation_state_repository.update(SimulationState.FAILED)
        # a restore adds a state of its own, the newest one is the state of the run
        restored = RepositoriesDB.create(server_config=server_config, simulation_config=replace(simulation_config, restore=True))
        restored.simulation_state_repository.update(SimulationState.FINISHED)

    @staticmethod
    def file_repository(directory: Path, simulator_name: str) -> MeasurementRepositoryFile:
        return MeasurementRepositoryFile.create(
            directory=directory,
            simulator_name=simulator_name,
            communication_protocol=CommunicationProtocol.TCP_SOCKET,
        )

    def values_of(self, simulator_name: str, step: int) -> tuple[ProtocolInterfaceValue, ...]:
        temperature = 270.0 + step
        if simulator_name == self.weather:
            return (ProtocolInterfaceValue(name="T_out", value=temperature), ProtocolInterfaceValue(name="profile", value=[1.0, 2.0, 3.0 + step]))
        # a third uses every digit of a float, so a lost digit shows
        return (ProtocolInterfaceValue(name="T_room", value=290.0 + step / 3), ProtocolInterfaceValue(name="T_out_in", value=temperature))

    def _write_steps(self, repository: MeasurementRepository, simulator_name: str, steps: int) -> None:
        for step in range(steps):
            repository.add(values=self.values_of(simulator_name=simulator_name, step=step), timestamp=StoredRun.time_of(step))
