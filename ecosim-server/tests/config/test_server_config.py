from pathlib import Path

import pytest
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.server_config import ServerConfig
from ecosim_test_common.resources.config_files import config_file_path, config_file_path_str
from tests.data.generate_server_config import generate_server_config_from_file_and_cli_arguments


def test_load_relative_paths() -> None:
    config = ServerConfig.of_cli_args(
        CLIArguments(
            passed_arguments=[
                "--server-config",
                str(config_file_path("server_config.ini")),
                "--simulation-config",
                str(config_file_path("simulation.json")),
                "--steps",
                "100",
                "--pace",
                "1.0",
            ],
        ),
    )

    # SERVER
    assert config.server.port == 1234

    # DATABASE
    assert config.database.host == "localhost"
    assert config.database.port == 5432
    assert config.database.username == "postgres"
    assert config.database.password == "integration_test"
    assert config.database.ssl is True


def test_load_absolute_paths() -> None:
    config = ServerConfig.of_cli_args(
        CLIArguments(
            passed_arguments=[
                "--server-config",
                config_file_path_str("server_config.ini"),
                "--simulation-config",
                config_file_path_str("simulation.json"),
                "--steps",
                "100",
                "--pace",
                "1.0",
            ],
        ),
    )

    # SERVER
    assert config.server.port == 1234

    # DATABASE
    assert config.database.host == "localhost"
    assert config.database.port == 5432
    assert config.database.username == "postgres"
    assert config.database.password == "integration_test"
    assert config.database.ssl is True


def test_overwrite_port() -> None:
    config = generate_server_config_from_file_and_cli_arguments(port="999")
    assert config.server.port == 999


def test_the_database_type_of_the_config_file_is_used() -> None:
    assert generate_server_config_from_file_and_cli_arguments().database.type is DatabaseType.POSTGRES


def test_the_database_type_can_be_overwritten_to_file() -> None:
    config = generate_server_config_from_file_and_cli_arguments(database_type=DatabaseType.FILE.serialized)

    assert config.database.type is DatabaseType.FILE


def test_the_database_type_can_be_overwritten_to_postgres() -> None:
    config = generate_server_config_from_file_and_cli_arguments(database_type=DatabaseType.POSTGRES.serialized)

    assert config.database.type is DatabaseType.POSTGRES


def test_an_unknown_database_type_fails() -> None:
    with pytest.raises(ValueError):
        generate_server_config_from_file_and_cli_arguments(database_type="mysql")


def test_the_default_database_directory_is_used_if_the_config_file_has_none() -> None:
    assert generate_server_config_from_file_and_cli_arguments().database.directory == Path("simulation_results")


def test_the_database_directory_can_be_overwritten() -> None:
    config = generate_server_config_from_file_and_cli_arguments(database_directory="/tmp/ecosim_results")

    assert config.database.directory == Path("/tmp/ecosim_results")
