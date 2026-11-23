import argparse
import dataclasses
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Sequence

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.readable_count import readable_count
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_server.config.database_cli_parameters import RESULTS
from ecosim_server.config.simulation_config import SimulationConfig

from ecosim.check.check_report import findings_lines, summary_line
from ecosim.check.checked_simulator import CheckedSimulator
from ecosim.check.simulation_check import SimulationCheck, simulators_of
from ecosim.command import command_parser
from ecosim.report_lines import command_text, ecosim_program, with_shown_paths
from ecosim.run.simulation_run import SimulationRun
from ecosim.run_directory import RunDirectory
from ecosim.server_arguments import split_server_options
from ecosim.simulation_command_line import SimulationCommandLine
from ecosim.simulation_directory import SimulationDirectory
from ecosim.simulation_options import RunOptions, add_run_options, add_simulation_options, server_parameter, setup_of


def build_parser() -> EcosimArgumentParser:
    parser = command_parser(
        name="run",
        description="Runs a simulation locally. Starts the server and one client per simulator. Logs are in the run folder. "
        + "Options after -- are passed to ecosim-server.",
        examples=(
            "ecosim run building --steps 100",
            "ecosim run building --duration 365d --step-size 1h",
            "ecosim run building --steps 100 --database-type postgres -- --database-schema run_2",
        ),
    )
    add_simulation_options(parser=parser)
    results_directory = AppConfigParameter(
        name="results",
        group=RESULTS,
        metavar="FOLDER",
        help_text="The run folder for the results and the logs. Default: a new folder in SIMULATION/results.",
    )
    add_run_options(parser=parser, results_parameters=[results_directory])
    no_check = AppConfigParameter(name="no-check", is_flag=True, help_text="Starts without checking the simulation first.")
    run_port = dataclasses.replace(server_parameter(name="port"), help_text="The port the server listens on. Default: a free port.")
    parser.add_parameters(parameters=[no_check, run_port], environment_variables=os.environ)
    return parser


def main(passed_arguments: Sequence[str]) -> int:
    parser = build_parser()
    command_line = SimulationCommandLine.of_arguments(parser=parser, passed_arguments=passed_arguments, command_name="run")
    options, simulation, run_options = command_line.options, command_line.simulation, command_line.run_options
    reason = _reason_not_to_start(options=options, simulation=simulation, run_options=run_options)
    if reason is not None:
        parser.error(reason)
    run_directory = _run_directory(options=options, simulation=simulation)
    if options.results is None and run_options.restore and not run_directory.path.exists():
        print(f"There is no earlier run in {simulation.results}. This is a new run.")
    checked = _check_and_print_findings(simulation=simulation, run_options=run_options, without_check=options.no_check)
    if checked is None:
        return ShutdownManager.FAILED_RUN_EXIT_CODE
    simulators, simulation_config = checked
    simulation_run = SimulationRun(
        simulation=simulation,
        run_options=run_options,
        run_directory=run_directory,
        port=options.port or get_free_port(),
        simulators=simulators,
    )
    return simulation_run.execute(simulation_config=simulation_config, restore_command=_restore_command(passed_arguments=passed_arguments))


def _reason_not_to_start(options: argparse.Namespace, simulation: SimulationDirectory, run_options: RunOptions) -> str | None:
    setup = setup_of(simulation_config_file=simulation.simulation_config)
    # with --duration the check reports an unreadable delta_t
    if run_options.steps is None and options.duration is None and setup is not None and "steps" not in setup:
        return f'set the length of the run with --steps or --duration, or add "steps" to setup in {simulation.simulation_config}'
    if options.port is not None and _is_in_use(port=options.port):
        return f"localhost:{options.port} is in use. Leave out --port to get a free one"
    if options.results is not None and RunDirectory(path=Path(options.results)).has_a_run() and not run_options.restore:
        how_to_go_on = "Choose another folder with --results, or continue that run with --restore-simulation-run"
        return f"{options.results} already contains the results of a run. {how_to_go_on}"
    return None


def _is_in_use(port: int) -> bool:
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("localhost", port))
        except OSError:
            return True
    return False


def _run_directory(options: argparse.Namespace, simulation: SimulationDirectory) -> RunDirectory:
    if options.results is not None:
        return RunDirectory(path=Path(options.results))
    newest = RunDirectory.newest(results=simulation.results) if options.restore_simulation_run else None
    return newest or RunDirectory.new_in(results=simulation.results, start=datetime.now())


def _check_and_print_findings(
    simulation: SimulationDirectory,
    run_options: RunOptions,
    without_check: bool,
) -> tuple[list[CheckedSimulator], SimulationConfig | None] | None:
    if without_check:
        simulators, findings = simulators_of(
            simulation=simulation,
            clients=SimulationConfig.clients_of_file(simulation_config_file=simulation.simulation_config),
        )
        simulation_config = None
    else:
        check = SimulationCheck.of_simulation(simulation=simulation, run_options=run_options, before_a_run=True)
        print(with_shown_paths(text=summary_line(check=check, simulation=simulation)))
        simulators, findings, simulation_config = check.simulators, check.findings, check.simulation_config
    for line in findings_lines(findings=findings):
        print(with_shown_paths(text=line))
    if not findings.problems:
        return simulators, simulation_config
    start_anyway = "" if without_check else " Use --no-check to start anyway."
    print(f"Found {readable_count(count=len(findings.problems), noun='problem')}. Nothing was started.{start_anyway}")
    return None


def _restore_command(passed_arguments: Sequence[str]) -> str:
    own_arguments, server_options = split_server_options(passed_arguments=passed_arguments)
    restore = [] if "--restore-simulation-run" in own_arguments else ["--restore-simulation-run"]
    return command_text(arguments=[*ecosim_program(), "run", *own_arguments, *restore, *(["--", *server_options] if server_options else [])])
