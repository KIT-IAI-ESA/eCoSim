from __future__ import annotations

from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.server_config import DatabaseConfig, MainConfig, ServerConfig
from ecosim_test_common.resources.config_files import config_file_path_str

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 1234
DEFAULT_DATABASE_PORT = 5432
DEFAULT_DATABASE_USERNAME = "postgres"
DEFAULT_DATABASE_PASSWORD = "integration_test"
DEFAULT_DATABASE_SCHEMA = "sim_control"


def generate_server_config(
    host: str | None = None,
    port: int | None = None,
    communication_protocol: CommunicationProtocol | None = None,
    image_renderer_port: int | None = None,
    image_renderer_interval: int | None = None,
    database_host: str | None = None,
    database_port: int | None = None,
    database_ssl: bool | None = None,
    database_drop_existing_schema: bool | None = None,
    database_username: str | None = None,
    database_password: str | None = None,
    database_schema: str | None = None,
    database_name: str | None = None,
    database_type: DatabaseType | None = None,
    database_directory: Path | None = None,
) -> ServerConfig:
    """Creates a `ServerConfig` without config files, so a test only names the values it cares about."""
    return ServerConfig(
        server=MainConfig(
            host=host or DEFAULT_HOST,
            port=port or DEFAULT_PORT,
            communication_protocol=communication_protocol or CommunicationProtocol.TCP_SOCKET,
            image_renderer_port=image_renderer_port,
            image_renderer_interval=image_renderer_interval,
        ),
        database=DatabaseConfig(
            # an empty host is the local socket of PostgreSQL
            host=database_host if database_host is not None else DEFAULT_HOST,
            port=database_port or DEFAULT_DATABASE_PORT,
            # a bool cannot be defaulted with 'or', because that would turn an explicit 'False' into the default
            ssl=database_ssl if database_ssl is not None else False,
            drop_existing_schema=database_drop_existing_schema if database_drop_existing_schema is not None else False,
            username=database_username or DEFAULT_DATABASE_USERNAME,
            password=database_password or DEFAULT_DATABASE_PASSWORD,
            schema=database_schema or DEFAULT_DATABASE_SCHEMA,
            # these fields declare a default, so 'DatabaseConfig' itself is the single source of truth for them
            name=database_name or DatabaseConfig.name,
            type=database_type or DatabaseConfig.type,
            directory=database_directory or DatabaseConfig.directory,
        ),
    )


def write_server_config_file(
    directory: Path,
    host: str = DEFAULT_HOST,
    port: int | str = DEFAULT_DATABASE_PORT,
    username: str = DEFAULT_DATABASE_USERNAME,
    password: str | None = DEFAULT_DATABASE_PASSWORD,
    ssl: bool = False,
) -> Path:
    file = directory / "server.ini"
    password_line = "" if password is None else f"password={password}\n"
    file.write_text(
        f"[server]\nport={DEFAULT_PORT}\n[database]\nserver={host}\nport={port}\nusername={username}\n{password_line}ssl={ssl}\n",
        encoding="utf-8",
    )
    return file


def generate_server_config_from_file_and_cli_arguments(
    config_file: str = config_file_path_str("server_config.ini"),
    simulation_file: str = config_file_path_str("simulation.json"),
    **additional_arguments: str,
) -> ServerConfig:
    flattened_args = []
    for key, value in additional_arguments.items():
        flattened_args.extend([f"--{key.replace('_', '-')}", str(value)])

    return ServerConfig.of_cli_args(
        CLIArguments(
            passed_arguments=[
                "--server-config",
                config_file,
                "--simulation-config",
                simulation_file,
                "--steps",
                "100",
                *flattened_args,
            ],
        ),
    )
