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
from ecosim.results.results_directory import results_directory_of
from ecosim.simulation_directory import missing_directory_message
from ecosim.simulation_options import server_parameter

RESULTS_IN_POSTGRES = "results in PostgreSQL"

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
        "directory",
        metavar="FOLDER",
        nargs="?",
        help="A simulation folder for its newest run, a run folder, or a folder of result files. Default: the current folder.",
    )
    server_config = AppConfigParameter(
        name="server-config",
        group=RESULTS_IN_POSTGRES,
        metavar="FILE",
        help_text="The server config of the run, instead of FOLDER. Its [database] section says where the results are.",
    )
    parser.add_parameters(parameters=[server_config, *DATABASE_OVERWRITE_PARAMETERS], environment_variables=os.environ)


def reason_not_to_read(options: argparse.Namespace) -> str | None:
    if options.server_config is not None:
        return "pass either FOLDER or --server-config, not both" if options.directory is not None else None
    # --database-type file changes nothing for a FOLDER
    if database_overwrite_of(options=options) not in (DbConfigOverwrite(), DbConfigOverwrite(_type=DatabaseType.FILE)):
        return "the --database options need --server-config"
    directory = Path(options.directory or ".")
    if directory.is_file():
        return f"{directory} is a file. Pass its folder {directory.parent}."
    if not directory.is_dir():
        return missing_directory_message(directory=directory)
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
    results: Path | DatabaseConfig

    @staticmethod
    def of_options(options: argparse.Namespace) -> ResultsSource:
        if options.server_config is None:
            return ResultsSource(results=results_directory_of(directory=Path(options.directory or ".")))
        server_config = Path(options.server_config)
        database = DatabaseConfig.from_config(config=ConfigParser(server_config), db_overwrite=database_overwrite_of(options=options))
        if database.type is DatabaseType.POSTGRES:
            return ResultsSource(results=database)
        if not database.directory.is_dir():
            where = f"A server with {shown_path(path=server_config)} writes its result files there. Pass the folder they are in instead."
            raise FileNotFoundError(f"{shown_path(path=database.directory)} does not exist. {where}")
        return ResultsSource(results=results_directory_of(directory=database.directory))

    def read(self, simulation_config: str | None) -> ResultTable:
        # with the inputs, to tell a left-out input from an unknown name
        if isinstance(self.results, DatabaseConfig):
            return read_database_results(database=self.results, simulation_config=simulation_config, include_inputs=True)
        return read_file_results(directory=self.results, simulation_config=simulation_config, include_inputs=True)

    def description(self) -> str:
        if isinstance(self.results, DatabaseConfig):
            return self.results.results_location()
        return shown_path(path=self.results)
