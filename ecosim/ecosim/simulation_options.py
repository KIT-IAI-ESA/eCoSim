"""The options that the ecosim commands share. The texts of the server's options are the server's own."""

from __future__ import annotations

import argparse
import dataclasses
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.shared_parameters import DEBUG_PARAMETER
from ecosim_common.tech.json.read_json_file import read_json_file
from ecosim_server.config.cli_parameters import CONFIG_FILES, RUN, RUN_PARAMETERS
from ecosim_server.config.database_cli_parameters import DATABASE_PARAMETERS

from ecosim.run_length import Duration, duration, step_size_in_milliseconds, steps_of_duration

SIMULATION_FILE_PARAMETERS = (
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
        help_text="The folder with one folder for each simulator, instead of SIMULATION/Modules.",
    ),
)


def server_parameter(name: str) -> AppConfigParameter:
    return next(parameter for parameter in (*RUN_PARAMETERS, *DATABASE_PARAMETERS) if parameter.name == name)


# the server writes to PostgreSQL by default, a run on this computer needs no database
DATABASE_TYPE_PARAMETER = dataclasses.replace(
    server_parameter(name="database-type"),
    help_text="Where the results go. Overrides type in the [database] section of the server config. If neither sets it, file.",
)


def add_simulation_options(parser: EcosimArgumentParser) -> None:
    parser.add_argument(
        "simulation",
        metavar="SIMULATION",
        nargs="?",
        help="The simulation folder, which holds server/ and Modules/. Without it, the current folder.",
    )
    parser.add_parameters(parameters=[DEBUG_PARAMETER, *SIMULATION_FILE_PARAMETERS], environment_variables=os.environ)


def add_run_options(parser: EcosimArgumentParser) -> None:
    run_options = parser.add_argument_group(title=RUN)
    length_options = run_options.add_mutually_exclusive_group()
    _add_server_option(container=length_options, name="steps")
    length_options.add_argument(
        "--duration",
        type=duration,
        metavar="DURATION",
        help="How much simulated time the run covers, like 90min, 12h or 365d, instead of --steps. It has to be a whole number of steps.",
    )
    run_options.add_argument(
        "--step-size",
        type=step_size_in_milliseconds,
        metavar="DURATION",
        help="The simulated time of one step, like 15min or 1s. A number without a unit is milliseconds. "
        + "Overrides setup.delta_t in the simulation config.",
    )
    _add_server_option(container=run_options, name="pace")
    _add_server_option(container=run_options, name="restore-simulation-run")
    parser.add_parameters(parameters=[DATABASE_TYPE_PARAMETER], environment_variables=os.environ)


class _OptionContainer(Protocol):
    """A parser or a group of its options."""

    def add_argument(self, *name_or_flags: str, **settings: Any) -> argparse.Action: ...


def _add_server_option(container: _OptionContainer, name: str) -> None:
    parameter = server_parameter(name=name)
    container.add_argument(parameter.to_cli_variable(), **parameter.argparse_settings(environment_variables=os.environ))


@dataclass(frozen=True)
class RunOptions:
    """The options of a run, as ecosim check checks it and ecosim run starts it."""

    # from --steps or --duration, None if neither is given
    steps: int | None
    step_size_in_milliseconds: int | None
    pace: float
    database_type: str | None
    restore: bool
    debug: bool
    server_options: list[str]

    @staticmethod
    def of_options(options: argparse.Namespace, server_options: list[str], simulation_config_file: Path) -> RunOptions:
        """Raises argparse.ArgumentTypeError for a duration that is not a whole number of steps."""
        return RunOptions(
            steps=_steps_of(
                steps=options.steps,
                run_duration=options.duration,
                step_size=options.step_size,
                simulation_config_file=simulation_config_file,
            ),
            step_size_in_milliseconds=options.step_size,
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
    return None if step_size is None else steps_of_duration(run_duration=run_duration, step_size_in_milliseconds=step_size)


def _delta_t_of(simulation_config_file: Path) -> int | None:
    try:
        return int(read_json_file(file=simulation_config_file)["setup"]["delta_t"])
    except (OSError, ValueError, KeyError, TypeError):
        # the check names what is wrong with the file
        return None
