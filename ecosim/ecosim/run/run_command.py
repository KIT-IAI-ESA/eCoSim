import argparse
import dataclasses
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import Sequence

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.shared_parameters import SERVER_CONNECTION
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.readable_count import readable_count
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_server.config.cli_parameters import SERVER_ADDRESS_PARAMETERS
from ecosim_server.config.database_cli_parameters import RESULTS
from ecosim_server.config.simulation_config import SimulationConfig

from ecosim.check.check_report import findings_lines, summary_line
from ecosim.check.checked_simulator import CheckedSimulator
from ecosim.check.simulation_check import SimulationCheck, simulators_of
from ecosim.command import command_parser
from ecosim.report_lines import command_text, ecosim_program, with_shown_paths
from ecosim.run.simulation_run import SimulationRun
from ecosim.run_folder import RunFolder
from ecosim.server_arguments import split_server_options
from ecosim.simulation_command_line import SimulationCommandLine
from ecosim.simulation_folder import SimulationFolder
from ecosim.simulation_options import RunOptions, add_run_options, add_simulation_options, setup_of


def build_parser() -> EcosimArgumentParser:
    parser = command_parser(
        name="run",
        description="Runs a simulation on this computer. It checks the simulation, starts the server and a client for every simulator, "
        + "shows the progress, and stops every part when one of them fails or on Ctrl-C. Each part writes its output to a log file "
        + "in the run folder. The options after -- go to ecosim-server.",
        examples=(
            "ecosim run building --steps 100",
            "ecosim run building --duration 365d --step-size 1h",
            "ecosim run building --steps 100 --database-type postgres -- --database-schema run_2",
        ),
    )
    add_simulation_options(parser=parser)
    results_folder = AppConfigParameter(
        name="results",
        group=RESULTS,
        metavar="FOLDER",
        help_text="The run folder for the results and the logs. Without it, a new folder in SIMULATION/results named after the start time, "
        + "or with --restore-simulation-run the newest one there.",
    )
    add_run_options(parser=parser, results_parameters=[results_folder])
    port = next(parameter for parameter in SERVER_ADDRESS_PARAMETERS if parameter.name == "port")
    no_check = AppConfigParameter(name="no-check", is_flag=True, help_text="Starts without checking the simulation first.")
    run_port = dataclasses.replace(port, group=SERVER_CONNECTION, help_text="The port the server listens on. Without it, a free port.")
    parser.add_parameters(parameters=[no_check, run_port], environment_variables=os.environ)
    return parser


def main(passed_arguments: Sequence[str]) -> int:
    parser = build_parser()
    command_line = SimulationCommandLine.of_arguments(parser=parser, passed_arguments=passed_arguments, command_name="run")
    options, simulation, run_options = command_line.options, command_line.simulation, command_line.run_options
    reason = _reason_not_to_start(options=options, simulation=simulation, run_options=run_options)
    if reason is not None:
        parser.error(reason)
    run_folder = _run_folder(options=options, simulation=simulation)
    checked = _checked_simulators(simulation=simulation, run_options=run_options, without_check=options.no_check)
    if checked is None:
        return ShutdownManager.FAILED_RUN_EXIT_CODE
    simulators, simulation_config = checked
    simulation_run = SimulationRun(
        simulation=simulation,
        run_options=run_options,
        run_folder=run_folder,
        port=options.port or get_free_port(),
        simulators=simulators,
    )
    return simulation_run.execute(simulation_config=simulation_config, restore_command=_restore_command(passed_arguments=passed_arguments))


def _reason_not_to_start(options: argparse.Namespace, simulation: SimulationFolder, run_options: RunOptions) -> str | None:
    setup = setup_of(simulation_config_file=simulation.simulation_config)
    # with --duration and an unreadable delta_t the steps are not known, and the check names the delta_t
    if run_options.steps is None and options.duration is None and setup is not None and "steps" not in setup:
        return f'give the length of the run with --steps or --duration, or add "steps" to setup in {simulation.simulation_config}'
    if options.port is not None and _is_in_use(port=options.port):
        return f"localhost:{options.port} is in use. Leave out --port to get a free one"
    if options.results is not None and RunFolder(path=Path(options.results)).holds_a_run() and not run_options.restore:
        how_to_go_on = "Choose another folder with --results, or continue that run with --restore-simulation-run"
        return f"{options.results} already holds the results of a run. {how_to_go_on}"
    return None


def _is_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("localhost", port))
        except OSError:
            return True
    return False


def _run_folder(options: argparse.Namespace, simulation: SimulationFolder) -> RunFolder:
    if options.results is not None:
        return RunFolder(path=Path(options.results))
    newest = RunFolder.newest(results=simulation.results) if options.restore_simulation_run else None
    if options.restore_simulation_run and newest is None:
        # what the server does too when it has nothing to restore
        print(f"There is no earlier run in {simulation.results}, so this is a new run.")
    return newest or RunFolder.new_in(results=simulation.results, start=datetime.now())


def _checked_simulators(
    simulation: SimulationFolder,
    run_options: RunOptions,
    without_check: bool,
) -> tuple[list[CheckedSimulator], SimulationConfig | None] | None:
    """The simulators to start and the loaded simulation config, None if a problem stops the run."""
    if without_check:
        # the clients cannot start without their folders and the kinds of their models
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
    it_or_them = "it" if len(findings.problems) == 1 else "them"
    start_anyway = "" if without_check else ", or start anyway with --no-check"
    print(f"Found {readable_count(count=len(findings.problems), noun='problem')}, so nothing was started. Fix {it_or_them}{start_anyway}.")
    return None


def _restore_command(passed_arguments: Sequence[str]) -> str:
    own_arguments, server_options = split_server_options(passed_arguments=passed_arguments)
    restore = [] if "--restore-simulation-run" in own_arguments else ["--restore-simulation-run"]
    return command_text(arguments=[*ecosim_program(), "run", *own_arguments, *restore, *(["--", *server_options] if server_options else [])])
