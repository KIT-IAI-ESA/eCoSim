import argparse
import dataclasses
import os
from pathlib import Path
from typing import Sequence

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.config.shared_parameters import DEBUG_PARAMETER, SERVER_CONNECTION
from ecosim_server.config.cli_parameters import RUN, SERVER_ADDRESS_PARAMETERS

from ecosim.check.simulation_check import SimulationCheck
from ecosim.command import command_parser
from ecosim.new.delayed_input import DelayedInput
from ecosim.new.loops import ensure_no_loop
from ecosim.new.new_report import NewReport
from ecosim.new.simulation_file import SimulationFile
from ecosim.new.new_simulation_files import NewSimulationFiles, ensure_the_folder_is_new
from ecosim.new.simulation_length import DEFAULT_DURATION, DEFAULT_START_DATE, DEFAULT_STEP_SIZE, SimulationLength, start_date
from ecosim.new.simulation_model import SimulationModel
from ecosim.new.wiring import Wiring
from ecosim.run_length import duration, step_size_in_milliseconds
from ecosim.simulation_folder import SimulationFolder
from ecosim.simulation_options import RunOptions, server_parameter


def build_parser() -> EcosimArgumentParser:
    parser = command_parser(
        name="new",
        description="Writes a simulation folder from FMUs: a folder in Modules/ for each FMU with the FMU, its .fmc file and its client config, "
        + "and server/ with the server config and simulation.json. An input is connected to the one output of another model "
        + "with the same name, where '.' and '_' count as the same. Every other input keeps the start value of its FMU. "
        + "At the end it checks the simulation as ecosim check does.",
        examples=(
            "ecosim new my_simulation house.fmu occupancy.fmu weather.fmu --duration 1y --start-date 2023-01-01",
            "ecosim new my_simulation models --step-size 1min --steps 200",
            "ecosim new two_houses weather.fmu house=house.fmu house2=house.fmu",
            "ecosim new plant_simulation plant.fmu controller.fmu --connect controller.T=plant.T_out --logical-delay controller.T=293.15",
        ),
    )
    # the simulation is required here, the FMUs follow it, and nothing goes to the server
    parser.usage = "%(prog)s [options] SIMULATION FMU [FMU ...]"
    parser.add_argument("simulation", metavar="SIMULATION", help="The simulation folder to write. It must not exist yet, or be empty.")
    parser.add_argument(
        "fmus",
        metavar="FMU",
        nargs="+",
        help="An FMU file, a folder whose .fmu files are all taken, or NAME=FILE to give the model another name than its file.",
    )
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
        help="Gives a connected input the value of the step before, which breaks a loop of models that feed each other. "
        + "START is its value in the first step, by default its start value in the FMU. Can be given several times.",
    )


def _add_length_options(parser: EcosimArgumentParser) -> None:
    run_options = parser.add_argument_group(title=RUN)
    run_options.add_argument(
        "--step-size",
        type=step_size_in_milliseconds,
        metavar="DURATION",
        help=f"The simulated time of one step, like 15min or 1s. A number without a unit is milliseconds. Without it, {DEFAULT_STEP_SIZE}.",
    )
    length_options = run_options.add_mutually_exclusive_group()
    length_options.add_argument(
        "--duration",
        type=duration,
        metavar="DURATION",
        help=f"How much simulated time the simulation covers, like 12h, 30d or 1y, where 1y is 365 days. Without it and --steps, {DEFAULT_DURATION}.",
    )
    length_options.add_argument(
        "--steps",
        type=ConfigParser.positive_whole_number,
        metavar="N",
        help="How many steps the simulation runs, instead of --duration.",
    )
    run_options.add_argument(
        "--start-date",
        type=start_date,
        metavar="DATE",
        help="When the simulated time starts, like 2023-01-01 or 2023-01-01T06:00+01:00. A time without an offset is UTC. "
        + f"The results of the first step are one step later. Without it, {DEFAULT_START_DATE}.",
    )


def _server_parameters() -> list[AppConfigParameter]:
    port = next(parameter for parameter in SERVER_ADDRESS_PARAMETERS if parameter.name == "port")
    return [
        dataclasses.replace(
            server_parameter(name="database-type"),
            default_value=DatabaseType.FILE.serialized,
            help_text="Where the results go, written to type in the [database] section of the server config.",
        ),
        dataclasses.replace(
            server_parameter(name="database-directory"),
            default_value="results/by_hand",
            help_text=f"With --database-type {DatabaseType.FILE.serialized}: the folder for the result files of a server started by hand, "
            + "relative to the folder it starts in. ecosim run puts each run in a folder of its own in results instead.",
        ),
        dataclasses.replace(
            port,
            group=SERVER_CONNECTION,
            default_value="1234",
            help_text="The port of the server, written to the server config and to every client config. ecosim run picks a free one instead.",
        ),
    ]


def main(passed_arguments: Sequence[str]) -> int:
    parser = build_parser()
    options = parser.parse_args(passed_arguments)
    simulation = SimulationFolder.of_path(path=Path(options.simulation))
    ensure_the_folder_is_new(simulation=simulation)
    length = _length_of(options=options, parser=parser)
    models = SimulationModel.of_arguments(arguments=options.fmus)
    wiring = Wiring.of_models(models=models, given_connections=options.connect or [])
    delayed = DelayedInput.of_texts(texts=options.logical_delay or [], models=models, wiring=wiring)
    ensure_no_loop(connections=wiring.connections, delayed=delayed)
    new_simulation_files = NewSimulationFiles(
        port=options.port,
        database_type=DatabaseType.of(options.database_type),
        database_directory=options.database_directory,
    )
    new_simulation_files.write(
        simulation=simulation,
        models=models,
        simulation_file=SimulationFile(models=models, wiring=wiring, delayed=delayed, length=length),
    )
    check = SimulationCheck.of_simulation(simulation=simulation, run_options=_run_options_of_the_check(debug=options.debug))
    print("\n".join(NewReport(simulation=simulation, models=models, wiring=wiring, delayed=delayed, length=length, check=check).lines()))
    return 1 if check.findings.problems else 0


def _length_of(options: argparse.Namespace, parser: EcosimArgumentParser) -> SimulationLength:
    try:
        return SimulationLength.of_options(options=options)
    except argparse.ArgumentTypeError as error:
        parser.error(str(error))


def _run_options_of_the_check(debug: bool) -> RunOptions:
    # a run without options, which takes everything from the files just written
    return RunOptions(steps=None, step_size_in_milliseconds=None, pace=1.0, database_type=None, restore=False, debug=debug, server_options=[])
