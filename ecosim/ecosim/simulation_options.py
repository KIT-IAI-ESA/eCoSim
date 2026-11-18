from __future__ import annotations

import argparse
import dataclasses
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.shared_parameters import DEBUG_PARAMETER
from ecosim_common.tech.json.read_json_file import read_json_file
from ecosim_server.config.cli_parameters import CONFIG_FILES, RUN, RUN_PARAMETERS, SERVER_ADDRESS_PARAMETERS
from ecosim_server.config.database_cli_parameters import DATABASE_PARAMETERS

from ecosim.run_length import Duration, duration, step_size_in_ms, steps_of_duration


def server_parameter(name: str) -> AppConfigParameter:
    return next(parameter for parameter in (*RUN_PARAMETERS, *SERVER_ADDRESS_PARAMETERS, *DATABASE_PARAMETERS) if parameter.name == name)


def add_simulation_options(parser: EcosimArgumentParser) -> None:
    parser.add_argument(
        "simulation",
        metavar="SIMULATION",
        nargs="?",
        help="The simulation folder with server/ and modules/. Default: the current folder.",
    )
    simulation_file_parameters = (
        AppConfigParameter(
            name="simulation-config",
            group=CONFIG_FILES,
            metavar="FILE",
            help_text="The simulation config, instead of SIMULATION/server/simulation.json.",
        ),
        AppConfigParameter(
            name="server-config",
            group=CONFIG_FILES,
            metavar="FILE",
            help_text="The server config, instead of SIMULATION/server/preferences.ini.",
        ),
        AppConfigParameter(
            name="simulator-dir",
            group=CONFIG_FILES,
            metavar="FOLDER",
            help_text="The folder with one folder for each simulator, instead of SIMULATION/modules.",
        ),
    )
    parser.add_parameters(parameters=[DEBUG_PARAMETER, *simulation_file_parameters], environment_variables=os.environ)


def add_run_options(parser: EcosimArgumentParser, results_parameters: Sequence[AppConfigParameter] = ()) -> None:
    run_options = parser.add_argument_group(title=RUN)
    length_options = run_options.add_mutually_exclusive_group()
    _add_server_option(container=length_options, name="steps")
    length_options.add_argument(
        "--duration",
        type=duration,
        metavar="DURATION",
        help="The simulated time of the run, like 90min, 12h or 365d. Must be a whole number of steps.",
    )
    run_options.add_argument(
        "--step-size",
        type=step_size_in_ms,
        metavar="DURATION",
        help="The simulated time of one step, like 15min or 1s, or a number in milliseconds. Overrides setup.delta_t in the simulation config.",
    )
    _add_server_option(container=run_options, name="pace")
    _add_server_option(container=run_options, name="restore-simulation-run")
    # the default of ecosim-server is postgres
    database_type = dataclasses.replace(
        server_parameter(name="database-type"),
        help_text="Where the results go. Overrides type in the [database] section of the server config. Default: file.",
    )
    parser.add_parameters(parameters=[database_type, *results_parameters], environment_variables=os.environ)


class _OptionContainer(Protocol):
    def add_argument(self, *name_or_flags: str, **settings: Any) -> argparse.Action: ...


def _add_server_option(container: _OptionContainer, name: str) -> None:
    parameter = server_parameter(name=name)
    container.add_argument(parameter.to_cli_variable(), **parameter.argparse_settings(environment_variables=os.environ))


@dataclass(frozen=True)
class RunOptions:
    steps: int | None
    step_size_in_ms: int | None
    pace: float
    database_type: str | None
    restore: bool
    debug: bool
    server_options: list[str]

    @staticmethod
    def of_options(options: argparse.Namespace, server_options: list[str], simulation_config_file: Path) -> RunOptions:
        return RunOptions(
            steps=_steps_of(
                steps=options.steps,
                run_duration=options.duration,
                step_size=options.step_size,
                simulation_config_file=simulation_config_file,
            ),
            step_size_in_ms=options.step_size,
            pace=options.pace,
            database_type=options.database_type,
            restore=options.restore_simulation_run,
            debug=options.debug,
            server_options=server_options,
        )


def _steps_of(steps: int | None, run_duration: Duration | None, step_size: int | None, simulation_config_file: Path) -> int | None:
    if run_duration is None:
        return steps
    step_size = step_size or _delta_t_of(simulation_config_file=simulation_config_file)
    return None if step_size is None else steps_of_duration(run_duration=run_duration, step_size_in_ms=step_size)


def setup_of(simulation_config_file: Path) -> dict[str, Any] | None:
    try:
        setup = read_json_file(file=simulation_config_file)["setup"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return setup if isinstance(setup, dict) else None


def _delta_t_of(simulation_config_file: Path) -> int | None:
    setup = setup_of(simulation_config_file=simulation_config_file) or {}
    try:
        return int(setup["delta_t"])
    except (KeyError, TypeError, ValueError):
        return None
