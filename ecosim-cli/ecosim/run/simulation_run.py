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
from ecosim.report_lines import command_text, length_line, shown_path, with_shown_paths
from ecosim.results.read_command import read_command_of_run
from ecosim.run.local_run import LocalRun, RunOutcome
from ecosim.run.process_programs import client_program, server_program
from ecosim.run.run_process import ProcessToStart
from ecosim.run.run_summary import summary_lines
from ecosim.run_directory import RunDirectory
from ecosim.server_arguments import server_arguments
from ecosim.simulation_directory import SimulationDirectory
from ecosim.simulation_options import RunOptions


@dataclass(frozen=True)
class SimulationRun:
    simulation: SimulationDirectory
    run_options: RunOptions
    run_directory: RunDirectory
    port: int
    simulators: list[CheckedSimulator]

    def execute(self, simulation_config: SimulationConfig | None, restore_command: str) -> int:
        arguments = server_arguments(
            simulation=self.simulation,
            run_options=self.run_options,
            port=self.port,
            database_directory=self.run_directory.path,
        )
        local_run = LocalRun(
            server=ProcessToStart(
                name="server",
                command=[*server_program(), *arguments],
                log_file=self.run_directory.log_file_of(process_name="server"),
            ),
            clients=[self._client(simulator=simulator) for simulator in self.simulators],
        )
        database = _database_of(server_arguments=arguments)
        self._prepare_the_run_directory(database=database)
        self._print_the_start(simulation_config=simulation_config)
        outcome = self._execute_with_temporary_files(local_run=local_run)
        self._print_the_summary(outcome=outcome, database=database, restore_command=restore_command)
        return outcome.exit_code

    def _prepare_the_run_directory(self, database: DatabaseConfig | None) -> None:
        if self.run_options.restore and self.run_directory.has_changed(simulation_config=self.simulation.simulation_config):
            copy = shown_path(path=self.run_directory.simulation_config_copy)
            print(
                f"{shown_path(path=self.simulation.simulation_config)} changed since this run started. "
                + f"If the restore fails, put back the copy {copy} or start a new run without --restore-simulation-run.",
            )
        # for results as files the server copies the simulation config itself
        self.run_directory.create(
            simulation_config=self.simulation.simulation_config,
            copies_the_simulation_config=database is not None and database.type is DatabaseType.POSTGRES,
        )

    def _execute_with_temporary_files(self, local_run: LocalRun) -> RunOutcome:
        temporary_files = self.run_directory.temporary_files
        # a tmp folder that was there before may belong to the user
        made_here = not temporary_files.exists()
        temporary_files.mkdir(exist_ok=True)
        try:
            return local_run.execute(working_directory=self.run_directory.path, environment=self._environment())
        finally:
            if made_here:
                shutil.rmtree(temporary_files, ignore_errors=True)

    def _print_the_start(self, simulation_config: SimulationConfig | None) -> None:
        length = f": {length_line(simulation_config=simulation_config)}" if simulation_config is not None else "."
        print(f"Run {self.run_directory.path.name}{length}")
        print(
            f"Started the server and {readable_count(count=len(self.simulators), noun='client')}. Logs: {shown_path(path=self.run_directory.logs)}",
            flush=True,
        )

    def _print_the_summary(self, outcome: RunOutcome, database: DatabaseConfig | None, restore_command: str) -> None:
        results_location = database.results_location() if database is not None else str(self.run_directory.path)
        server_options = self.run_options.server_options
        read_command = read_command_of_run(
            simulation=self.simulation,
            run_directory=self.run_directory,
            database=database,
            server_options=server_options,
        )
        lines = summary_lines(
            outcome=outcome,
            results_location=results_location,
            restore_command=restore_command,
            read_command=command_text(arguments=read_command),
        )
        for line in lines:
            print(with_shown_paths(text=line))

    def _client(self, simulator: CheckedSimulator) -> ProcessToStart:
        command = [
            *client_program(client_type=simulator.client_type, simulator_directory_path=simulator.directory.path),
            *("--config-file", str(simulator.directory.config_parser.config_file.absolute())),
            *("--server-host", "localhost", "--server-port", str(self.port)),
            *("--communication-protocol", CommunicationProtocol.TCP_SOCKET.serialized),
            *DEBUG_PARAMETER.to_passed_arguments(self.run_options.debug),
        ]
        return ProcessToStart(name=simulator.name, command=command, log_file=self.run_directory.log_file_of(process_name=simulator.name))

    def _environment(self) -> dict[str, str]:
        temporary_files = str(self.run_directory.temporary_files.absolute())
        # UTF-8 for the banner in a log file on Windows
        return {**os.environ, "PYTHONUTF8": "1", "TMPDIR": temporary_files, "TMP": temporary_files, "TEMP": temporary_files}


def _database_of(server_arguments: list[str]) -> DatabaseConfig | None:
    try:
        return ServerConfig.of_cli_args(CLIArguments(passed_arguments=server_arguments)).database
    except Exception:
        return None
