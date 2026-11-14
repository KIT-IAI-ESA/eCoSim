from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.measurement.postgres_name_check import postgres_name_problems

from ecosim.check.findings import Findings, problem_of, problem_of_ini_file
from ecosim.check.simulation_file_check import SimulationFileCheck
from ecosim.server_arguments import server_arguments
from ecosim.simulation_folder import SimulationFolder
from ecosim.simulation_options import RunOptions


@dataclass(frozen=True)
class ServerSideCheck:
    """The config files of the server, read as ecosim-server reads them from the arguments of a run."""

    server_config: ServerConfig | None
    simulation_config: SimulationConfig | None
    # the simulators of simulation.json, also when its connections are wrong, None if they cannot be read
    clients: list[ClientSimulatorConfig] | None
    findings: Findings

    @staticmethod
    def of_simulation(simulation: SimulationFolder, run_options: RunOptions, simulation_file: SimulationFileCheck, port: int) -> ServerSideCheck:
        checked_run = dataclasses.replace(run_options, steps=simulation_file.steps_for_the_check(run_options=run_options))
        arguments = CLIArguments(
            passed_arguments=server_arguments(simulation=simulation, run_options=checked_run, port=port, database_directory=simulation.results),
        )
        findings = Findings()
        server_config = _server_config_of(arguments=arguments, simulation=simulation, findings=findings)
        simulation_config = (
            _simulation_config_of(arguments=arguments, simulation=simulation, findings=findings) if simulation_file.can_be_loaded() else None
        )
        if server_config is not None and simulation_config is not None and server_config.database.type is DatabaseType.POSTGRES:
            findings.problems += [
                f"{simulation.simulation_config}: {problem}" for problem in postgres_name_problems(simulation_config=simulation_config)
            ]
        return ServerSideCheck(
            server_config=server_config,
            simulation_config=simulation_config,
            clients=simulation_config.clients
            if simulation_config is not None
            else _clients_of(simulation_file=simulation_file, simulation=simulation),
            findings=findings,
        )


def _server_config_of(arguments: CLIArguments, simulation: SimulationFolder, findings: Findings) -> ServerConfig | None:
    try:
        return ServerConfig.of_cli_args(arguments)
    except Exception as error:
        # every error of the loader is a problem of the simulation
        findings.problems.append(problem_of_ini_file(error=error, ini_file=simulation.server_config))
        return None


def _simulation_config_of(arguments: CLIArguments, simulation: SimulationFolder, findings: Findings) -> SimulationConfig | None:
    try:
        # as ecosim-server reads it
        return SimulationConfig.of_config_file_and_params(
            simulation_config_file=arguments.simulation_config(),
            steps=arguments.simulation_steps(),
            step_size_override=arguments.step_size_override(),
            pace=arguments.pace(),
            restore=arguments.restore_simulation_run(),
        )
    except Exception as error:
        findings.problems.append(problem_of(error=error, file=simulation.simulation_config))
        return None


def _clients_of(simulation_file: SimulationFileCheck, simulation: SimulationFolder) -> list[ClientSimulatorConfig] | None:
    if simulation_file.raw_config is None:
        return None
    try:
        return SimulationConfig.clients_of_file(simulation_config_file=simulation.simulation_config)
    except Exception:
        # the problems of the file are named already
        return None
