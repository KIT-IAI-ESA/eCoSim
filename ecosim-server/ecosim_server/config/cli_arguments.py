from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any

from ecosim_common.config.app_config import AppConfig, AppConfigParameter
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.db_config_overwrite import DbConfigOverwrite


class CLIArguments(AppConfig):
    def __init__(
        self,
        passed_arguments: List[Any] | None = None,
    ):
        super().__init__(
            passed_arguments=passed_arguments or sys.argv[1:],
            cli_description="This is the server of eCoSimPy.",
            parameters=[
                AppConfigParameter(
                    name="server-config",
                    required=True,
                    help_text="The path to the config file. This must be relative to the call path or it can be an "
                    "absolute path.",
                ),
                AppConfigParameter(
                    name="simulation-config",
                    required=True,
                    help_text="The path to the simulation config file. This must be relative to the call path or it can"
                    " be an absolute path.",
                ),
                AppConfigParameter(
                    name="host",
                    help_text="The host for the server. Note: this will override any settings in config files.",
                ),
                AppConfigParameter(
                    name="port",
                    transform=lambda x: int(x),
                    help_text="The port for the server. Note: this will override any port in config files.",
                ),
                AppConfigParameter(
                    name="steps",
                    required=True,
                    transform=lambda x: int(x),
                    help_text="The number of steps that the simulation should run.",
                ),
                AppConfigParameter(
                    name="step-size",
                    transform=lambda x: int(x),
                    help_text="The step size in milliseconds.",
                ),
                AppConfigParameter(
                    name="pace",
                    required=False,
                    default_value="1.0",
                    transform=lambda x: float(x),
                    help_text="The execution pace - the value must be between 0 and 1. E.g. 1 means 100%, 0.7 means 70%",
                ),
                AppConfigParameter(
                    name="debug",
                    is_flag=True,
                    help_text="enabling debug mode (more logs)",
                ),
                AppConfigParameter(
                    name="database-host",
                    help_text="The database host",
                ),
                AppConfigParameter(
                    name="database-port",
                    help_text="The database port",
                ),
                AppConfigParameter(
                    name="database-user",
                    help_text="The database user",
                ),
                AppConfigParameter(
                    name="database-user-password",
                    help_text="The database user password",
                ),
                AppConfigParameter(
                    name="database-name",
                    help_text="The name of the database",
                ),
                AppConfigParameter(
                    name="database-schema",
                    help_text="The name of the database schema",
                ),
                AppConfigParameter(
                    name="database-ssl",
                    default_value="False",
                    transform=lambda x: ConfigParser.config_string_to_bool(x),
                    help_text="If SSL should be used when connecting to the DB",
                ),
                AppConfigParameter(
                    name="database-drop-existing-schema",
                    is_flag=True,
                    help_text="This will drop existing schemas - WARNING: you can lose data with this option, this is mainly a development option.",
                ),
                AppConfigParameter(
                    name="image-renderer-port",
                    default_value=None,
                    required=False,
                    transform=lambda x: int(x),
                    help_text="The port for the image renderer socket. If not set no image rendering socket will be opened.",
                ),
                AppConfigParameter(
                    name="image-renderer-interval",
                    default_value=None,
                    required=False,
                    transform=lambda x: int(x),
                    help_text="The interval (in time_steps) that the images will be rendered and sent over the image rendering socket. "
                    + "If not set no images will be sent.",
                ),
                AppConfigParameter(
                    name="restore-simulation-run",
                    default_value=None,
                    required=False,
                    is_flag=True,
                    help_text="If this flag is used, a possible previous aborted simulation run will be restored. If there is no previous "
                    + "simulation run, the simulation is executed normally.",
                ),
            ],
        )

    def server_config(self) -> Path:
        path: Path = Path(self._args.server_config)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def simulation_config(self) -> Path:
        path: Path = Path(self._args.simulation_config)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def simulation_steps(self) -> int:
        return self._args.steps

    def step_size_override(self) -> int | None:
        return self._args.step_size

    def pace(self) -> float:
        return self._args.pace

    def debug_enabled(self) -> bool:
        return self._args.debug

    def image_renderer_port(self) -> int | None:
        return self._args.image_renderer_port

    def image_renderer_interval(self) -> int | None:
        return self._args.image_renderer_interval

    def restore_simulation_run(self) -> bool:
        return self._args.restore_simulation_run

    @property
    def port(self) -> int | None:
        return self._args.port

    def db_config_overwrite(self) -> DbConfigOverwrite:
        return DbConfigOverwrite(
            _host=self._args.database_host,
            _port=self._args.database_port,
            _user=self._args.database_user,
            _user_password=self._args.database_user_password,
            _name=self._args.database_name,
            _schema=self._args.database_schema,
            _ssl=self._args.database_ssl,
            _drop_existing_schema=self._args.database_drop_existing_schema,
        )

    def config_overrides(self) -> ServerConfigOverride:
        return ServerConfigOverride(
            server_host=self._args.host,
            server_port=self._args.port,
        )


# TODO_AFTER_MERGE: find common abstraction with existing CLIArguments
class CLIArgumentsHPC(AppConfig):
    def __init__(
        self,
        passed_arguments: List[Any] | None = None,
    ):
        super().__init__(
            passed_arguments=passed_arguments or sys.argv[1:],
            cli_description="This is the server of eCoSimPy.",
            parameters=[
                AppConfigParameter(
                    name="server-config",
                    required=True,
                    help_text="The path to the config file. This must be relative to the call path or it can be an "
                    "absolute path.",
                ),
                AppConfigParameter(
                    name="simulation-config",
                    required=True,
                    help_text="The path to the simulation config file. This must be relative to the call path or it can"
                    " be an absolute path.",
                ),
                AppConfigParameter(
                    name="simulator-dir",
                    required=True,
                    help_text="The path to the directory containing all simulators. This must be a relative to the call"
                    " path or it can be an absolute path.",
                ),
                AppConfigParameter(
                    name="host",
                    help_text="The host for the server. Note: this will override any settings in config files.",
                ),
                AppConfigParameter(
                    name="port",
                    transform=lambda x: int(x),
                    help_text="The port for the server. Note: this will override any port in config files.",
                ),
                AppConfigParameter(
                    name="steps",
                    required=True,
                    transform=lambda x: int(x),
                    help_text="The number of steps that the simulation should run.",
                ),
                AppConfigParameter(
                    name="step-size",
                    transform=lambda x: int(x),
                    help_text="The step size in milliseconds.",
                ),
                AppConfigParameter(
                    name="pace",
                    required=False,
                    default_value="1.0",
                    transform=lambda x: float(x),
                    help_text="The execution pace - the value must be between 0 and 1. E.g. 1 means 100%, 0.7 means 70%",
                ),
                AppConfigParameter(
                    name="debug",
                    is_flag=True,
                    help_text="enabling debug mode (more logs)",
                ),
                AppConfigParameter(
                    name="database-host",
                    help_text="The database host",
                ),
                AppConfigParameter(
                    name="database-port",
                    help_text="The database port",
                ),
                AppConfigParameter(
                    name="database-user",
                    help_text="The database user",
                ),
                AppConfigParameter(
                    name="database-user-password",
                    help_text="The database user password",
                ),
                AppConfigParameter(
                    name="database-name",
                    help_text="The name of the database",
                ),
                AppConfigParameter(
                    name="database-schema",
                    help_text="The name of the database schema",
                ),
                AppConfigParameter(
                    name="database-ssl",
                    default_value="False",
                    transform=lambda x: ConfigParser.config_string_to_bool(x),
                    help_text="If SSL should be used when connecting to the DB",
                ),
                AppConfigParameter(
                    name="database-drop-existing-schema",
                    is_flag=True,
                    help_text="This will drop existing schemas - WARNING: you can lose data with this option, this is mainly a development option.",
                ),
                AppConfigParameter(
                    name="image-renderer-port",
                    default_value=None,
                    required=False,
                    transform=lambda x: int(x),
                    help_text="The port for the image renderer socket. If not set no image rendering socket will be opened.",
                ),
                AppConfigParameter(
                    name="image-renderer-interval",
                    default_value=None,
                    required=False,
                    transform=lambda x: int(x),
                    help_text="The interval (in time_steps) that the images will be rendered and sent over the image rendering socket. "
                    + "If not set no images will be sent.",
                ),
                AppConfigParameter(
                    name="restore-simulation-run",
                    default_value=None,
                    required=False,
                    is_flag=True,
                    help_text="If this flag is used, a possible previous aborted simulation run will be restored. If there is no previous "
                    + "simulation run, the simulation is executed normally.",
                ),
                AppConfigParameter(
                    name="interactive",
                    is_flag=True,
                    help_text="Establishes interactive version of Dask-MPI. If not set, the simulation will run in batch mode.",
                ),
            ],
        )

    def server_config(self) -> Path:
        path: Path = Path(self._args.server_config)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def simulation_config(self) -> Path:
        path: Path = Path(self._args.simulation_config)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def simulation_steps(self) -> int:
        return self._args.steps

    def step_size_override(self) -> int | None:
        return self._args.step_size

    def pace(self) -> float:
        return self._args.pace

    def debug_enabled(self) -> bool:
        return self._args.debug

    def image_renderer_port(self) -> int | None:
        return self._args.image_renderer_port

    def image_renderer_interval(self) -> int | None:
        return self._args.image_renderer_interval

    def restore_simulation_run(self) -> bool:
        return self._args.restore_simulation_run

    def interactive(self) -> bool:
        return self._args.interactive

    @property
    def port(self) -> int | None:
        return self._args.port

    def db_config_overwrite(self) -> DbConfigOverwrite:
        return DbConfigOverwrite(
            _host=self._args.database_host,
            _port=self._args.database_port,
            _user=self._args.database_user,
            _user_password=self._args.database_user_password,
            _name=self._args.database_name,
            _schema=self._args.database_schema,
            _ssl=self._args.database_ssl,
            _drop_existing_schema=self._args.database_drop_existing_schema,
        )

    def config_overrides(self) -> ServerConfigOverride:
        return ServerConfigOverride(
            server_host=self._args.host,
            server_port=self._args.port,
        )


@dataclass(frozen=True)
class ServerConfigOverride:
    server_host: str | None
    server_port: int | None
