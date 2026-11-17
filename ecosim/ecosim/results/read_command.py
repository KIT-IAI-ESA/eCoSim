import argparse
from pathlib import Path
from typing import Sequence

from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.server_config import DatabaseConfig

from ecosim.report_lines import ecosim_program
from ecosim.results.results_directory import is_a_simulation, postgres_read_command
from ecosim.results.results_source import DATABASE_OVERWRITE_PARAMETERS
from ecosim.run_directory import RunDirectory
from ecosim.simulation_directory import SimulationDirectory


def read_command_of_run(
    simulation: SimulationDirectory,
    run_directory: RunDirectory,
    database: DatabaseConfig | None,
    server_options: Sequence[str],
) -> list[str]:
    if database is not None and database.type is DatabaseType.POSTGRES:
        database_options = database_options_of(server_options=server_options)
        return postgres_read_command(server_config=str(simulation.server_config), run_directory=run_directory, database_options=database_options)
    if is_a_simulation(directory=simulation.path) and RunDirectory.newest(results=simulation.results) == run_directory:
        return [*ecosim_program(), "results", *([] if simulation.path == Path(".") else [str(simulation.path)])]
    return [*ecosim_program(), "results", str(run_directory.path)]


def database_options_of(server_options: Sequence[str]) -> list[str]:
    # a printed command must not show the password
    parameters = [parameter for parameter in DATABASE_OVERWRITE_PARAMETERS if parameter.name != "database-user-password"]
    parser = argparse.ArgumentParser(add_help=False)
    for parameter in parameters:
        parser.add_argument(parameter.to_cli_variable(), **parameter.argparse_settings(environment_variables={}))
    options, _ = parser.parse_known_args(server_options)
    return [argument for parameter in parameters for argument in parameter.to_passed_arguments(getattr(options, parameter.to_parsed_arg_name()))]
