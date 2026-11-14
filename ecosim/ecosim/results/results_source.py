"""Where ecosim results finds the results of a run: a folder of result files or a PostgreSQL schema."""

from __future__ import annotations

import argparse
import dataclasses
import os
from dataclasses import dataclass
from pathlib import Path

from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.config.db_config_overwrite import DbConfigOverwrite
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.results import ResultTable, read_database_results, read_file_results

from ecosim.report_lines import shown_path
from ecosim.results.results_folder import results_folder_of
from ecosim.simulation_folder import missing_folder_message
from ecosim.simulation_options import server_parameter

RESULTS_IN_POSTGRES = "results in PostgreSQL"

# the options of ecosim-server that change where its results are, with the texts of the server
DATABASE_OVERWRITE_PARAMETERS = tuple(
    dataclasses.replace(server_parameter(name=name), group=RESULTS_IN_POSTGRES)
    for name in (
        "database-type",
        "database-host",
        "database-port",
        "database-user",
        "database-user-password",
        "database-name",
        "database-schema",
        "database-ssl",
    )
)


def add_source_options(parser: EcosimArgumentParser) -> None:
    parser.add_argument(
        "folder",
        metavar="FOLDER",
        nargs="?",
        help="A simulation folder for its newest run, a run folder, or a folder of result files. Without it, the current folder.",
    )
    server_config = AppConfigParameter(
        name="server-config",
        group=RESULTS_IN_POSTGRES,
        metavar="FILE",
        help_text="The server config of the run, instead of FOLDER. Its [database] section says where the results are.",
    )
    parser.add_parameters(parameters=[server_config, *DATABASE_OVERWRITE_PARAMETERS], environment_variables=os.environ)


def reason_the_options_name_no_results(options: argparse.Namespace) -> str | None:
    """Why the options do not say where the results are, None if they do."""
    if options.server_config is not None:
        return "give either FOLDER or --server-config, not both" if options.folder is not None else None
    # a FOLDER holds result files, so --database-type file changes nothing
    if database_overwrite_of(options=options) not in (DbConfigOverwrite(), DbConfigOverwrite(_type=DatabaseType.FILE)):
        return "the --database options change what the server config says, so give it with --server-config"
    folder = Path(options.folder or ".")
    if folder.is_file():
        return f"{folder} is a file. Give the folder that holds it: {folder.parent}"
    if not folder.is_dir():
        return missing_folder_message(folder=folder)
    return None


def database_overwrite_of(options: argparse.Namespace) -> DbConfigOverwrite:
    return DbConfigOverwrite(
        _host=options.database_host,
        _port=options.database_port,
        _user=options.database_user,
        _user_password=options.database_user_password,
        _name=options.database_name,
        _schema=options.database_schema,
        _ssl=options.database_ssl,
        _type=None if options.database_type is None else DatabaseType.of(options.database_type),
    )


@dataclass(frozen=True)
class ResultsSource:
    """A folder of result files, or the PostgreSQL schema that the server config and the --database options name."""

    results: Path | DatabaseConfig

    @staticmethod
    def of_options(options: argparse.Namespace) -> ResultsSource:
        if options.server_config is None:
            return ResultsSource(results=results_folder_of(folder=Path(options.folder or ".")))
        server_config = Path(options.server_config)
        database = DatabaseConfig.from_config(config=ConfigParser(path=server_config), db_overwrite=database_overwrite_of(options=options))
        if database.type is DatabaseType.POSTGRES:
            return ResultsSource(results=database)
        if not database.directory.is_dir():
            where = f"A server with {shown_path(path=server_config)} writes its result files there. Give the folder they are in instead."
            raise FileNotFoundError(f"{shown_path(path=database.directory)} does not exist. {where}")
        return ResultsSource(results=results_folder_of(folder=database.directory))

    def read(self, simulation_config: str | None) -> ResultTable:
        """With the inputs, so that asking for a left-out input can say how to show it."""
        if isinstance(self.results, DatabaseConfig):
            return read_database_results(database=self.results, simulation_config=simulation_config, include_inputs=True)
        return read_file_results(directory=self.results, simulation_config=simulation_config, include_inputs=True)

    def description(self) -> str:
        if isinstance(self.results, DatabaseConfig):
            return self.results.results_location()
        return shown_path(path=self.results)
