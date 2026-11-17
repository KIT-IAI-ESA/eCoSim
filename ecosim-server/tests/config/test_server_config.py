from pathlib import Path

import pytest
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.server_config import ServerConfig
from ecosim_test_common.resources.config_files import config_file_path, config_file_path_str
from tests.data.generate_server_config import generate_server_config_from_file_and_cli_arguments, write_server_config_file


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
    assert config.database.ssl is False


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
    assert config.database.ssl is False


@pytest.mark.parametrize("ssl", [True, False])
def test_the_ssl_key_of_the_config_file_is_used_without_the_option(
    tmp_path: Path,
    ssl: bool,
) -> None:
    config_file = write_server_config_file(directory=tmp_path, ssl=ssl)

    config = generate_server_config_from_file_and_cli_arguments(config_file=str(config_file))

    assert config.database.ssl is ssl


def test_the_option_false_overrides_a_config_file_that_says_true(tmp_path: Path) -> None:
    config = generate_server_config_from_file_and_cli_arguments(
        config_file=str(write_server_config_file(directory=tmp_path, ssl=True)),
        database_ssl="false",
    )

    assert config.database.ssl is False


def test_the_option_true_overrides_a_config_file_that_says_false(tmp_path: Path) -> None:
    config = generate_server_config_from_file_and_cli_arguments(
        config_file=str(write_server_config_file(directory=tmp_path, ssl=False)),
        database_ssl="true",
    )

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
    with pytest.raises(SystemExit) as exit_info:
        generate_server_config_from_file_and_cli_arguments(database_type="mysql")

    assert exit_info.value.code == USAGE_ERROR_EXIT_CODE


def test_the_default_database_directory_is_used_if_the_config_file_has_none() -> None:
    assert generate_server_config_from_file_and_cli_arguments().database.directory == Path("simulation_results")


def test_the_database_directory_can_be_overwritten() -> None:
    config = generate_server_config_from_file_and_cli_arguments(database_directory="/tmp/ecosim_results")

    assert config.database.directory == Path("/tmp/ecosim_results")


def test_the_database_port_option_overrides_an_empty_port_in_the_config_file(tmp_path: Path) -> None:
    config = generate_server_config_from_file_and_cli_arguments(
        config_file=str(write_server_config_file(directory=tmp_path, port="")),
        database_port="5433",
    )

    assert config.database.port == 5433
