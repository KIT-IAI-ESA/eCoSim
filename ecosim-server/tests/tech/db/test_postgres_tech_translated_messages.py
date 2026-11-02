from unittest.mock import MagicMock

import psycopg
import pytest
from ecosim_server.tech.db import postgres_tech
from ecosim_server.tech.db.postgres_tech import PostgresTech
from sqlalchemy.exc import OperationalError
from tests.data.generate_server_config import generate_server_config

MISSING_DATABASE_IN_GERMAN = "FATAL:  Datenbank »sim_control« existiert nicht"
WRONG_PASSWORD_IN_GERMAN = "FATAL:  Passwort-Authentifizierung für Benutzer »postgres« fehlgeschlagen"


def _error_with(message: str) -> OperationalError:
    return OperationalError(statement="connect", params={}, orig=psycopg.OperationalError(message))


@pytest.fixture
def target_engine() -> MagicMock:
    schema_connection = MagicMock()
    schema_connection.__enter__.return_value.execute.return_value.scalar.return_value = None
    engine = MagicMock()
    engine.connect.side_effect = [_error_with(MISSING_DATABASE_IN_GERMAN), schema_connection]
    return engine


@pytest.fixture
def root_connection() -> MagicMock:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = None
    return connection


@pytest.fixture
def root_engine(root_connection: MagicMock) -> MagicMock:
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = root_connection
    return engine


@pytest.fixture(autouse=True)
def create_engine(
    monkeypatch: pytest.MonkeyPatch,
    target_engine: MagicMock,
    root_engine: MagicMock,
) -> MagicMock:
    engine_factory = MagicMock(side_effect=[target_engine, root_engine])
    monkeypatch.setattr(postgres_tech, "create_engine", engine_factory)
    return engine_factory


def test_a_translated_missing_database_is_created_after_the_lookup(
    target_engine: MagicMock,
    root_engine: MagicMock,
    root_connection: MagicMock,
) -> None:
    PostgresTech(generate_server_config()).init_db()

    root_connection.exec_driver_sql.assert_called_once_with('CREATE DATABASE "sim_control"', execution_options={"no_parameters": True})
    root_engine.dispose.assert_called_once()
    target_engine.dispose.assert_called_once()


def test_a_translated_message_raises_the_original_error_if_the_lookup_finds_the_database(
    root_engine: MagicMock,
    root_connection: MagicMock,
) -> None:
    root_connection.execute.return_value.scalar.return_value = 1

    with pytest.raises(OperationalError, match="existiert nicht"):
        PostgresTech(generate_server_config()).init_db()

    root_connection.exec_driver_sql.assert_not_called()
    root_engine.dispose.assert_called_once()


def test_a_translated_message_raises_the_original_error_if_the_maintenance_database_fails(
    root_engine: MagicMock,
    root_connection: MagicMock,
) -> None:
    root_engine.connect.side_effect = _error_with("FATAL:  pg_hba.conf lehnt die Verbindung ab")

    with pytest.raises(OperationalError, match="existiert nicht") as error:
        PostgresTech(generate_server_config()).init_db()

    assert "pg_hba.conf" in str(error.value.__cause__)
    root_connection.exec_driver_sql.assert_not_called()
    root_engine.dispose.assert_called_once()


def test_a_translated_wrong_password_does_not_reach_the_maintenance_database(
    create_engine: MagicMock,
    target_engine: MagicMock,
) -> None:
    target_engine.connect.side_effect = [_error_with(WRONG_PASSWORD_IN_GERMAN)]

    with pytest.raises(OperationalError, match="fehlgeschlagen"):
        PostgresTech(generate_server_config()).init_db()

    create_engine.assert_called_once()
