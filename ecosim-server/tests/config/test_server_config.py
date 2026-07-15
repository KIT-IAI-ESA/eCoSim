from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.server_config import ServerConfig
from tests.tech.resource_utils import resource_path


def test_load_relative_paths() -> None:
    config = ServerConfig.of_cli_args(
        CLIArguments(
            passed_arguments=[
                "--server-config",
                f"{resource_path()}/server_config.ini",
                "--simulation-config",
                f"{resource_path()}/simulation.json",
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
                f"{resource_path()}/server_config.ini",
                "--simulation-config",
                f"{resource_path()}/simulation.json",
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
                f"{resource_path()}/server_config.ini",
                "--simulation-config",
                f"{resource_path()}/simulation.json",
                "--steps",
                "100",
                "--port",
                "999",
            ],
        ),
    )
    # SERVER
    assert config.server.port == 999
