from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.data.repositories_file_based import RepositoriesFileBased
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository import MODULE_PREFIX
from ecosim_server.measurement.measurement_repository_file import MeasurementRepositoryFile
from ecosim_server.results.result_column import ResultColumn
from ecosim_server.results.result_table import ResultTable
from ecosim_server.results.result_table_builder import ResultTableBuilder
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository_file import SimulationStateRepositoryFile

_logger = ESPLogger("FileResults")


def read_file_results(directory: str | Path, simulation_config: str | Path | None = None, include_inputs: bool = False) -> ResultTable:
    """Reads the result files of a run as one table, without the inputs by default."""
    given_config = None if simulation_config is None else Path(simulation_config)
    table = FileResults.of_directory(directory=Path(directory), simulation_config=given_config).table()
    return table if include_inputs else table.without_inputs()


@dataclass(frozen=True)
class FileResults:
    directory: Path
    simulation_config_file: Path | None
    clients: list[ClientSimulatorConfig] | None
    stored_simulator_names: list[str]

    @staticmethod
    def of_directory(directory: Path, simulation_config: Path | None) -> FileResults:
        if directory.is_file():
            raise NotADirectoryError(f"{directory} is a file. Pass its folder {directory.parent}.")
        if not directory.is_dir():
            raise FileNotFoundError(f"{directory} does not exist. Use the --database-directory of the run.")
        stored_simulator_names = FileResults._simulator_names_in(directory=directory)
        if not stored_simulator_names:
            raise FileNotFoundError(f"{directory} has no results. There is no {MODULE_PREFIX}<simulator>.jsonl in it.")
        config_file = FileResults._simulation_config_file_of(directory=directory, given_file=simulation_config)
        clients = None if config_file is None else SimulationConfig.clients_of_file(config_file)
        return FileResults(directory=directory, simulation_config_file=config_file, clients=clients, stored_simulator_names=stored_simulator_names)

    def table(self) -> ResultTable:
        builder = ResultTableBuilder()
        run_counts = [self._add_simulator(builder=builder, simulator_name=name) for name in self._names_to_read()]
        warnings = [*self._config_warnings(), *self._appended_runs_warnings(run_count=max(run_counts))]
        for warning in warnings:
            _logger.warning("%s", warning)
        return builder.build(state=self._state(), warnings=warnings)

    def _names_to_read(self) -> list[str]:
        if self.clients is None:
            return self.stored_simulator_names
        names = [client.simulator_name for client in self.clients if client.simulator_name in self.stored_simulator_names]
        if not names:
            listed = ", ".join(client.simulator_name for client in self.clients)
            raise ValueError(f"{self.directory} has no results of the simulators in {self.simulation_config_file}: {listed}.")
        return names

    def _add_simulator(self, builder: ResultTableBuilder, simulator_name: str) -> int:
        """Returns the number of runs in the file of the simulator."""
        # the protocol only picks the kind of lock
        protocol = CommunicationProtocol.TCP_SOCKET
        repository = MeasurementRepositoryFile.create(directory=self.directory, simulator_name=simulator_name, communication_protocol=protocol)
        entries, run_count = self._last_run_of(entries=repository.all())
        described_columns = self._described_columns(simulator_name=simulator_name)
        builder.add_simulator(simulator_name=simulator_name, entries=entries, described_columns=described_columns)
        return run_count

    def _described_columns(self, simulator_name: str) -> list[ResultColumn]:
        client = next((client for client in self.clients or [] if client.simulator_name == simulator_name), None)
        return [] if client is None else [ResultColumn.of_interface(interface) for interface in client.interfaces]

    def _config_warnings(self) -> list[str]:
        if self.clients is None:
            return [f"{self.directory} has no simulation.json. The table shows the inputs too. Pass the run's simulation.json to leave them out."]
        listed = [client.simulator_name for client in self.clients]
        stored, config_file = self.stored_simulator_names, self.simulation_config_file
        return [
            *(f"{self.directory} has no results of the simulator {name} in {config_file}." for name in listed if name not in stored),
            *(
                f"{config_file} does not list {name}. Its results in {MODULE_PREFIX}{name}.jsonl are left out."
                for name in stored
                if name not in listed
            ),
        ]

    def _appended_runs_warnings(self, run_count: int) -> list[str]:
        if run_count == 1:
            return []
        return [
            f"{self.directory} contains {run_count} runs. The table shows the last run. "
            + "Delete the folder before a run or use a separate --database-directory per run.",
        ]

    def _state(self) -> SimulationState | None:
        repository = SimulationStateRepositoryFile.create(directory=self.directory, communication_protocol=CommunicationProtocol.TCP_SOCKET)
        return repository.current() if repository.file_path().is_file() else None

    @staticmethod
    def _simulation_config_file_of(directory: Path, given_file: Path | None) -> Path | None:
        if given_file is not None:
            return given_file
        copy = RepositoriesFileBased.simulation_config_copy_in(directory=directory)
        return copy if copy.is_file() else None

    @staticmethod
    def _last_run_of(entries: list[MeasurementEntry]) -> tuple[list[MeasurementEntry], int]:
        run_starts = [position for position in range(1, len(entries)) if entries[position].timestamp <= entries[position - 1].timestamp]
        return entries[run_starts[-1] if run_starts else 0 :], len(run_starts) + 1

    @staticmethod
    def _simulator_names_in(directory: Path) -> list[str]:
        return sorted(file.name.removeprefix(MODULE_PREFIX).removesuffix(".jsonl") for file in directory.glob(f"{MODULE_PREFIX}*.jsonl"))
