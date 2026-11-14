"""The ecosim results command that reads the results of a run, which ecosim run prints at its end."""

import argparse
from pathlib import Path
from typing import Sequence

from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.server_config import DatabaseConfig

from ecosim.report_lines import ecosim_program
from ecosim.results.results_folder import is_a_simulation, postgres_read_command
from ecosim.results.results_source import DATABASE_OVERWRITE_PARAMETERS
from ecosim.run_folder import RunFolder
from ecosim.simulation_folder import SimulationFolder


def read_command_of_run(
    simulation: SimulationFolder,
    run_folder: RunFolder,
    database: DatabaseConfig | None,
    server_options: Sequence[str],
) -> list[str]:
    if database is not None and database.type is DatabaseType.POSTGRES:
        database_options = database_options_of(server_options=server_options)
        return postgres_read_command(server_config=str(simulation.server_config), run_folder=run_folder, database_options=database_options)
    if is_a_simulation(folder=simulation.path) and RunFolder.newest(results=simulation.results) == run_folder:
        # for a simulation, ecosim results shows its newest run
        return [*ecosim_program(), "results", *([] if simulation.path == Path(".") else [str(simulation.path)])]
    return [*ecosim_program(), "results", str(run_folder.path)]


def database_options_of(server_options: Sequence[str]) -> list[str]:
    """The --database options of a run, without the password, which a printed command must not show."""
    parameters = [parameter for parameter in DATABASE_OVERWRITE_PARAMETERS if parameter.name != "database-user-password"]
    parser = argparse.ArgumentParser(add_help=False)
    for parameter in parameters:
        parser.add_argument(parameter.to_cli_variable(), **parameter.argparse_settings(environment_variables={}))
    options, _ = parser.parse_known_args(server_options)
    return [argument for parameter in parameters for argument in parameter.to_passed_arguments(getattr(options, parameter.to_parsed_arg_name()))]
