from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.config.shared_parameters import DEBUG_PARAMETER
from ecosim_common.tech.readable_count import readable_count
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.server_config import DatabaseConfig, ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig

from ecosim.check.checked_simulator import CheckedSimulator
from ecosim.report_lines import length_line, shown_path, with_shown_paths
from ecosim.run.local_run import LocalRun, RunOutcome
from ecosim.run.part_programs import client_program, server_program
from ecosim.run.run_part import PartToStart
from ecosim.run.run_summary import summary_lines
from ecosim.run_folder import RunFolder
from ecosim.server_arguments import server_arguments
from ecosim.simulation_folder import SimulationFolder
from ecosim.simulation_options import RunOptions


@dataclass(frozen=True)
class SimulationRun:
    """A run of a simulation on this computer, with the logs of its parts in the run folder."""

    simulation: SimulationFolder
    run_options: RunOptions
    run_folder: RunFolder
    port: int
    simulators: list[CheckedSimulator]

    def execute(self, simulation_config: SimulationConfig | None, restore_command: str) -> int:
        arguments = server_arguments(
            simulation=self.simulation,
            run_options=self.run_options,
            port=self.port,
            database_directory=self.run_folder.path,
        )
        # every program is found before anything starts
        local_run = LocalRun(
            server=PartToStart(name="server", command=[*server_program(), *arguments], log_file=self.run_folder.log_file_of(part_name="server")),
            clients=[self._client(simulator=simulator) for simulator in self.simulators],
        )
        database = _database_of(server_arguments=arguments)
        self._prepare_the_run_folder(database=database)
        self._print_the_start(simulation_config=simulation_config)
        outcome = self._execute_with_temporary_files(local_run=local_run)
        results_location = database.results_location() if database is not None else str(self.run_folder.path)
        for line in summary_lines(outcome=outcome, results_location=results_location, restore_command=restore_command):
            print(with_shown_paths(text=line))
        return outcome.exit_code

    def _prepare_the_run_folder(self, database: DatabaseConfig | None) -> None:
        if self.run_options.restore and self.run_folder.has_changed(simulation_config=self.simulation.simulation_config):
            copy = shown_path(path=self.run_folder.simulation_config_copy)
            print(
                f"{shown_path(path=self.simulation.simulation_config)} changed since this run started, so the restore can fail. "
                + f"If it does, put back the copy {copy}, or start a new run without --restore-simulation-run.",
            )
        self.run_folder.create(
            simulation_config=self.simulation.simulation_config,
            copies_the_simulation_config=database is not None and database.type is DatabaseType.POSTGRES,
        )

    def _execute_with_temporary_files(self, local_run: LocalRun) -> RunOutcome:
        temporary_files = self.run_folder.temporary_files
        # a tmp folder that was there before can be the user's
        made_here = not temporary_files.exists()
        temporary_files.mkdir(exist_ok=True)
        try:
            return local_run.execute(working_folder=self.run_folder.path, environment=self._environment())
        finally:
            if made_here:
                shutil.rmtree(temporary_files, ignore_errors=True)

    def _print_the_start(self, simulation_config: SimulationConfig | None) -> None:
        length = f": {length_line(simulation_config=simulation_config)}" if simulation_config is not None else "."
        print(f"Run {self.run_folder.path.name}{length}")
        print(
            f"Started the server and {readable_count(count=len(self.simulators), noun='client')}. Logs: {shown_path(path=self.run_folder.logs)}",
            flush=True,
        )

    def _client(self, simulator: CheckedSimulator) -> PartToStart:
        command = [
            *client_program(client_type=simulator.client_type, simulator_folder=simulator.directory.path),
            *("--config-file", str(simulator.directory.config_parser.config_file.absolute())),
            *("--server-host", "localhost", "--server-port", str(self.port)),
            *("--communication-protocol", CommunicationProtocol.TCP_SOCKET.serialized),
            *DEBUG_PARAMETER.to_passed_arguments(self.run_options.debug),
        ]
        return PartToStart(name=simulator.name, command=command, log_file=self.run_folder.log_file_of(part_name=simulator.name))

    def _environment(self) -> dict[str, str]:
        temporary_files = str(self.run_folder.temporary_files.absolute())
        # UTF-8 for the block letters of the banner in a log file on Windows
        return {**os.environ, "PYTHONUTF8": "1", "TMPDIR": temporary_files, "TMP": temporary_files, "TEMP": temporary_files}


def _database_of(server_arguments: list[str]) -> DatabaseConfig | None:
    try:
        return ServerConfig.of_cli_args(CLIArguments(passed_arguments=server_arguments)).database
    except Exception:
        # the server names the problem in its log when it starts
        return None
