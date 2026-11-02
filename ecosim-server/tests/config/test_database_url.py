from pathlib import Path
from typing import Callable

import pytest
from ecosim_server.config.server_config import DatabaseConfig, ServerConfig
from sqlalchemy import URL, make_url
from tests.data.generate_server_config import generate_server_config, generate_server_config_from_file_and_cli_arguments, write_server_config_file
from tests.tech.db.special_passwords import SPECIAL_PASSWORDS

UrlGenerator = Callable[[DatabaseConfig], URL]
URL_GENERATORS = [DatabaseConfig.generate_sqlalchemy_db_url, DatabaseConfig.generate_sqlalchemy_root_url]


def _database_config(
    password: str = "hunter7",
    ssl: bool = False,
) -> DatabaseConfig:
    return generate_server_config(
        database_host="database-host",
        database_port=6543,
        database_username="simulation-user",
        database_password=password,
        database_name="simulation-results",
        database_ssl=ssl,
    ).database


@pytest.mark.parametrize("password", SPECIAL_PASSWORDS)
@pytest.mark.parametrize("generate_url", URL_GENERATORS)
def test_a_password_with_special_characters_stays_in_one_piece(
    generate_url: UrlGenerator,
    password: str,
) -> None:
    url = make_url(generate_url(_database_config(password=password)))

    assert url.password == password
    assert url.username == "simulation-user"
    assert url.host == "database-host"
    assert url.port == 6543


def test_the_database_url_goes_to_the_configured_database() -> None:
    assert make_url(_database_config().generate_sqlalchemy_db_url()).database == "simulation-results"


def test_the_root_url_goes_to_the_maintenance_database() -> None:
    assert make_url(_database_config().generate_sqlalchemy_root_url()).database == "postgres"


@pytest.mark.parametrize(("ssl", "sslmode"), [(True, "require"), (False, "disable")])
@pytest.mark.parametrize("generate_url", URL_GENERATORS)
def test_sslmode_follows_the_option(
    generate_url: UrlGenerator,
    ssl: bool,
    sslmode: str,
) -> None:
    url = make_url(generate_url(_database_config(ssl=ssl)))

    assert url.query["sslmode"] == sslmode


@pytest.mark.parametrize("generate_url", URL_GENERATORS)
def test_the_url_text_does_not_show_the_password(generate_url: UrlGenerator) -> None:
    url = generate_url(_database_config())

    assert "hunter7" not in str(url)
    assert "hunter7" not in repr(url)


def test_the_representation_of_the_config_does_not_show_the_password() -> None:
    config = generate_server_config(database_password="hunter7")

    assert "hunter7" not in repr(config)


@pytest.mark.parametrize("password", SPECIAL_PASSWORDS)
def test_a_password_from_the_config_file_reaches_the_url_unchanged(
    tmp_path: Path,
    password: str,
) -> None:
    config = ServerConfig.of_file(write_server_config_file(directory=tmp_path, password=password))

    assert make_url(config.database.generate_sqlalchemy_db_url()).password == password


@pytest.mark.parametrize("password", SPECIAL_PASSWORDS)
def test_a_password_from_the_command_line_reaches_the_url_unchanged(password: str) -> None:
    config = generate_server_config_from_file_and_cli_arguments(database_user_password=password)

    assert make_url(config.database.generate_sqlalchemy_db_url()).password == password
