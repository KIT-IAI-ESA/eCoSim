import argparse
import dataclasses
import os
from pathlib import Path
from typing import Sequence

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.config.shared_parameters import DEBUG_PARAMETER
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_server.config.cli_parameters import RUN

from ecosim.check.simulation_check import SimulationCheck
from ecosim.command import command_parser
from ecosim.new.delayed_input import DelayedInput
from ecosim.new.input_connections import InputConnections
from ecosim.new.loops import ensure_no_loop
from ecosim.new.new_report import NewReport
from ecosim.new.new_simulation_config import NewSimulationConfig
from ecosim.new.new_simulation_files import NewSimulationFiles, ensure_the_directory_is_new
from ecosim.new.simulation_length import DEFAULT_DURATION, DEFAULT_START_DAY, DEFAULT_STEP_SIZE, SimulationLength, start_date
from ecosim.new.simulation_model import SimulationModel
from ecosim.run_length import duration, step_size_in_ms
from ecosim.simulation_directory import SimulationDirectory
from ecosim.simulation_options import RunOptions, server_parameter


def build_parser() -> EcosimArgumentParser:
    parser = command_parser(
        name="new",
        description="Writes a simulation folder from FMUs. Connects each input to the output of another model with the same name. "
        + "Checks the result like ecosim check.",
        examples=(
            "ecosim new my_simulation house.fmu occupancy.fmu weather.fmu --duration 1y --start-date 2023-01-01",
            "ecosim new my_simulation models --step-size 1min --steps 200",
            "ecosim new two_houses weather.fmu house=house.fmu house2=house.fmu",
            "ecosim new plant_simulation plant.fmu controller.fmu --connect controller.T=plant.T_out --logical-delay controller.T=293.15",
        ),
    )
    parser.usage = "%(prog)s [options] SIMULATION FMU [FMU ...]"
    parser.add_argument("simulation", metavar="SIMULATION", help="The new simulation folder. Must be empty or not exist yet.")
    parser.add_argument("fmus", metavar="FMU", nargs="+", help="An FMU file, a folder with .fmu files, or NAME=FILE to name the model.")
    parser.add_parameters(parameters=[DEBUG_PARAMETER], environment_variables=os.environ)
    _add_length_options(parser=parser)
    _add_connection_options(parser=parser)
    parser.add_parameters(parameters=_server_parameters(), environment_variables=os.environ)
    return parser


def _add_connection_options(parser: EcosimArgumentParser) -> None:
    connection_options = parser.add_argument_group(title="connections")
    connection_options.add_argument(
        "--connect",
        action="append",
        metavar="INPUT=OUTPUT",
        help="Connects an input to an output of another name, like house.T_out=weather.T_dry. Can be given several times.",
    )
    connection_options.add_argument(
        "--logical-delay",
        action="append",
        metavar="INPUT[=START]",
        help="Gives a connected input the value of the previous step to break a loop. START is its value in the first step. "
        + "Can be given several times.",
    )


def _add_length_options(parser: EcosimArgumentParser) -> None:
    run_options = parser.add_argument_group(title=RUN)
    run_options.add_argument(
        "--step-size",
        type=step_size_in_ms,
        metavar="DURATION",
        help=f"The simulated time of one step, like 15min or 1s, or a number in milliseconds. Default: {DEFAULT_STEP_SIZE}.",
    )
    length_options = run_options.add_mutually_exclusive_group()
    length_options.add_argument(
        "--duration",
        type=duration,
        metavar="DURATION",
        help=f"The simulated time of the simulation, like 12h, 30d or 1y (365 days). Default: {DEFAULT_DURATION}.",
    )
    length_options.add_argument("--steps", type=ConfigParser.positive_whole_number, metavar="N", help="The number of steps, instead of --duration.")
    run_options.add_argument(
        "--start-date",
        type=start_date,
        metavar="DATE",
        help=f"The start of the simulated time, like 2023-01-01 or 2023-01-01T06:00+01:00. Default: {DEFAULT_START_DAY}.",
    )


def _server_parameters() -> list[AppConfigParameter]:
    return [
        dataclasses.replace(
            server_parameter(name="database-type"),
            default_value=DatabaseType.FILE.serialized,
            help_text="Where the results go, written to type in the [database] section of the server config.",
        ),
        dataclasses.replace(
            server_parameter(name="database-directory"),
            default_value="results/manual",
            help_text="The folder for the result files of a server started manually. ecosim run writes each run to its own folder in results.",
        ),
        dataclasses.replace(
            server_parameter(name="port"),
            default_value="1234",
            help_text="The port of the server, written to the server config and to every client config. ecosim run picks a free one instead.",
        ),
    ]


def main(passed_arguments: Sequence[str]) -> int:
    parser = build_parser()
    options = parser.parse_args(passed_arguments)
    simulation = SimulationDirectory.of_path(path=Path(options.simulation))
    ensure_the_directory_is_new(simulation=simulation)
    length = _length_of(options=options, parser=parser)
    models = SimulationModel.of_arguments(arguments=options.fmus)
    input_connections = InputConnections.of_models(models=models, given_connections=options.connect or [])
    delayed = DelayedInput.of_texts(texts=options.logical_delay or [], models=models, input_connections=input_connections)
    ensure_no_loop(connections=input_connections.connections, delayed=delayed)
    new_simulation_files = NewSimulationFiles(
        port=options.port,
        database_type=DatabaseType.of(options.database_type),
        database_directory=options.database_directory,
    )
    new_simulation_files.write(
        simulation=simulation,
        models=models,
        new_simulation_config=NewSimulationConfig(models=models, input_connections=input_connections, delayed=delayed, length=length),
    )
    run_options = RunOptions(steps=None, step_size_in_ms=None, pace=1.0, database_type=None, restore=False, debug=options.debug, server_options=[])
    check = SimulationCheck.of_simulation(simulation=simulation, run_options=run_options)
    print(
        "\n".join(
            NewReport(simulation=simulation, models=models, input_connections=input_connections, delayed=delayed, length=length, check=check).lines(),
        ),
    )
    return ShutdownManager.FAILED_RUN_EXIT_CODE if check.findings.problems else ShutdownManager.SUCCESS_EXIT_CODE


def _length_of(options: argparse.Namespace, parser: EcosimArgumentParser) -> SimulationLength:
    try:
        return SimulationLength.of_options(options=options)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))
