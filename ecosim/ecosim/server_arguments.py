"""The arguments ecosim check and ecosim run give ecosim-server, with the options after -- at the end."""

import argparse
from pathlib import Path
from typing import Sequence

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.config_parser import ConfigParser, ConfigParserException
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.config.shared_parameters import DEBUG_PARAMETER
from ecosim_server.config.cli_arguments import CLIArguments

from ecosim.simulation_folder import SimulationFolder
from ecosim.simulation_options import RunOptions, server_parameter

# the ecosim commands give the server these themselves, so they cannot come after --
SET_BY_THE_COMMAND = (
    "--server-config",
    "--simulation-config",
    "--host",
    "--port",
    "--communication-protocol",
    "--steps",
    "--step-size",
    "--pace",
    "--restore-simulation-run",
    "--debug",
    "--database-type",
    "--database-directory",
)


def split_server_options(passed_arguments: Sequence[str]) -> tuple[list[str], list[str]]:
    """The options of the command, and those after -- for ecosim-server, before argparse sees them."""
    arguments = list(passed_arguments)
    if "--" not in arguments:
        return arguments, []
    return arguments[: arguments.index("--")], arguments[arguments.index("--") + 1 :]


def reason_to_refuse(server_options: list[str], command_name: str, command_options: argparse.Namespace) -> str | None:
    """Why an option after -- cannot be passed on, None if every one can."""
    server_option_names = [parameter.to_cli_variable() for parameter in CLIArguments.parameters()]
    for given_name in (option.split("=")[0] for option in server_options if option.startswith("--")):
        # argparse takes a unique start of a name for the whole name
        named = [name for name in server_option_names if name == given_name] or [name for name in server_option_names if name.startswith(given_name)]
        if len(named) == 1 and named[0] in SET_BY_THE_COMMAND:
            instead = _what_to_do_instead(server_option=named[0], command_name=command_name, command_options=command_options)
            return f"{named[0]} after -- is set by ecosim {command_name}. {instead}"
    return None


def _what_to_do_instead(server_option: str, command_name: str, command_options: argparse.Namespace) -> str:
    own_option = "--results" if server_option == "--database-directory" else server_option
    if hasattr(command_options, own_option.removeprefix("--").replace("-", "_")):
        return f"Use ecosim {command_name} {own_option} instead."
    return "Leave it out."


def ensure_the_server_takes(server_options: list[str], command_parser: argparse.ArgumentParser) -> None:
    """Ends with the usage error of the command for an option that ecosim-server would not take."""
    parser = EcosimArgumentParser(prog=command_parser.prog, usage=command_parser.usage, add_help=False)
    passed_on = [parameter for parameter in CLIArguments.parameters() if parameter.to_cli_variable() not in SET_BY_THE_COMMAND]
    parser.add_parameters(parameters=passed_on, environment_variables={})
    parser.parse_args(server_options)


def server_arguments(simulation: SimulationFolder, run_options: RunOptions, port: int, database_directory: Path) -> list[str]:
    """Absolute paths, since the server of a run starts in the run folder."""
    return [
        *("--server-config", str(simulation.server_config.absolute()), "--simulation-config", str(simulation.simulation_config.absolute())),
        *("--host", "localhost", "--port", str(port), "--communication-protocol", CommunicationProtocol.TCP_SOCKET.serialized),
        *server_parameter(name="steps").to_passed_arguments(run_options.steps),
        *server_parameter(name="step-size").to_passed_arguments(run_options.step_size_in_milliseconds),
        *server_parameter(name="pace").to_passed_arguments(run_options.pace),
        *server_parameter(name="restore-simulation-run").to_passed_arguments(run_options.restore),
        *DEBUG_PARAMETER.to_passed_arguments(run_options.debug),
        *_database_type_arguments(run_options=run_options, server_config_file=simulation.server_config),
        # the server reads it only for results as files
        *("--database-directory", str(database_directory.absolute())),
        *run_options.server_options,
    ]


def _database_type_arguments(run_options: RunOptions, server_config_file: Path) -> list[str]:
    # the server reads the type of its config itself, and the default of the server is PostgreSQL
    if run_options.database_type is None and _sets_a_database_type(server_config_file=server_config_file):
        return []
    return ["--database-type", run_options.database_type or DatabaseType.FILE.serialized]


def _sets_a_database_type(server_config_file: Path) -> bool:
    try:
        return ConfigParser(server_config_file).contains("database", "type")
    except (OSError, ConfigParserException):
        # the check names what is wrong with the file
        return False
