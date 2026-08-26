import pytest
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.server_config import ServerConfig
from ecosim_test_common.resources.config_files import config_file_path_str, config_file_path


def create_config(*additional_arguments: str) -> ServerConfig:
    return ServerConfig.of_cli_args(
        CLIArguments(
            passed_arguments=[
                "--server-config",
                config_file_path_str("server_config.ini"),
                "--simulation-config",
                config_file_path_str("simulation.json"),
                "--steps",
                "100",
                *additional_arguments,
            ],
        ),
    )


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
    config = ServerConfig.of_cli_args(
        args=CLIArguments(
            passed_arguments=[
                "--server-config",
                config_file_path_str("server_config.ini"),
                "--simulation-config",
                config_file_path_str("simulation.json"),
                "--steps",
                "100",
                "--port",
                "999",
            ],
        ),
    )
    # SERVER
    assert config.server.port == 999


def test_the_database_type_of_the_config_file_is_used() -> None:
    assert create_config().database.type is DatabaseType.POSTGRES


def test_the_database_type_can_be_overwritten_to_file() -> None:
    config = create_config("--database-type", "file")

    assert config.database.type is DatabaseType.FILE


def test_the_database_type_can_be_overwritten_to_postgres() -> None:
    config = create_config("--database-type", "postgres")

    assert config.database.type is DatabaseType.POSTGRES


def test_an_unknown_database_type_fails() -> None:
    with pytest.raises(ValueError):
        create_config("--database-type", "mysql")
