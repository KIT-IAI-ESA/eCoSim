from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository_file import MeasurementRepositoryFile
from ecosim_server.results.result_column import ResultColumn
from ecosim_server.results.result_table import ResultTable
from ecosim_server.results.result_table_builder import ResultTableBuilder
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository_file import SimulationStateRepositoryFile

_logger = ESPLogger("FileResults")


def read_results(directory: str | Path, simulation_config: str | Path | None = None, include_inputs: bool = False) -> ResultTable:
    """The result files of a run as one table, by default without the inputs."""
    given_config = None if simulation_config is None else Path(simulation_config)
    table = FileResults.of_folder(directory=Path(directory), simulation_config=given_config).table()
    return table if include_inputs else table.without_inputs()


@dataclass(frozen=True)
class FileResults:
    """A folder of file results and the simulators of the run's simulation.json, None without one."""

    folder: Path
    simulation_config_file: Path | None
    clients: list[ClientSimulatorConfig] | None
    stored_simulator_names: list[str]

    @staticmethod
    def of_folder(directory: Path, simulation_config: Path | None) -> FileResults:
        if directory.is_file():
            raise NotADirectoryError(f"{directory} is a file. Give the folder that holds it: {directory.parent}.")
        if not directory.is_dir():
            raise FileNotFoundError(f"{directory} does not exist. Give the folder the server wrote the results to, its --database-directory.")
        stored_simulator_names = _simulator_names_in(directory)
        if not stored_simulator_names:
            raise FileNotFoundError(f"{directory} holds no results: there is no module_<simulator>.jsonl in it.")
        config_file = _simulation_config_file_of(directory=directory, given_file=simulation_config)
        clients = None if config_file is None else SimulationConfig.clients_of_file(config_file)
        return FileResults(folder=directory, simulation_config_file=config_file, clients=clients, stored_simulator_names=stored_simulator_names)

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
            raise ValueError(f"{self.folder} holds no results of the simulators that {self.simulation_config_file} lists: {listed}.")
        return names

    def _add_simulator(self, builder: ResultTableBuilder, simulator_name: str) -> int:
        """Returns how many runs the file of the simulator holds."""
        # the server has ended, so a lock of this process is enough
        protocol = CommunicationProtocol.TCP_SOCKET
        repository = MeasurementRepositoryFile.create(directory=self.folder, simulator_name=simulator_name, communication_protocol=protocol)
        entries, run_count = _last_run_of(repository.all())
        described_columns = self._described_columns(simulator_name=simulator_name)
        builder.add_simulator(simulator_name=simulator_name, entries=entries, described_columns=described_columns)
        return run_count

    def _described_columns(self, simulator_name: str) -> list[ResultColumn]:
        client = next((client for client in self.clients or [] if client.simulator_name == simulator_name), None)
        return [] if client is None else [ResultColumn.of_interface(interface) for interface in client.interfaces]

    def _config_warnings(self) -> list[str]:
        if self.clients is None:
            return [f"{self.folder} has no simulation.json, so the table shows the inputs too. Give the run's simulation.json to leave them out."]
        listed = [client.simulator_name for client in self.clients]
        stored, config_file = self.stored_simulator_names, self.simulation_config_file
        return [
            *(f"{self.folder} has no results of {name}, which {config_file} lists." for name in listed if name not in stored),
            *(f"{config_file} does not list {name}, so the table leaves out module_{name}.jsonl." for name in stored if name not in listed),
        ]

    def _appended_runs_warnings(self, run_count: int) -> list[str]:
        if run_count == 1:
            return []
        return [
            f"{self.folder} holds {run_count} runs, because the server adds each run to the files of the earlier ones. The table shows the last run. "
            + "Delete the folder before a run, or give each run its own --database-directory.",
        ]

    def _state(self) -> SimulationState | None:
        repository = SimulationStateRepositoryFile.create(directory=self.folder, communication_protocol=CommunicationProtocol.TCP_SOCKET)
        return repository.current() if repository.file_path().is_file() else None


def _simulation_config_file_of(directory: Path, given_file: Path | None) -> Path | None:
    if given_file is not None:
        return given_file
    copy = directory / "simulation.json"
    return copy if copy.is_file() else None


def _last_run_of(entries: list[MeasurementEntry]) -> tuple[list[MeasurementEntry], int]:
    """A run writes its steps in order, so a step that is not later than the one before starts the next run."""
    run_starts = [position for position in range(1, len(entries)) if entries[position].timestamp <= entries[position - 1].timestamp]
    return entries[run_starts[-1] if run_starts else 0 :], len(run_starts) + 1


def _simulator_names_in(folder: Path) -> list[str]:
    return sorted(file.name.removeprefix("module_").removesuffix(".jsonl") for file in folder.glob("module_*.jsonl"))
