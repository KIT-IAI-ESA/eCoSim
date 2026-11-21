from typing import Callable
from uuid import uuid4

import pytest
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.tech.db.postgres_tech import PostgresTech
from sqlalchemy import URL, create_engine, text
from sqlalchemy.exc import OperationalError
from tests.tech.db.postgres_test_cluster import PostgresTestCluster


def _is_encrypted(url: URL) -> bool:
    with create_engine(url).connect() as connection:
        return bool(connection.execute(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")).scalar())


def test_ssl_true_fails_against_a_server_without_tls(plain_cluster: PostgresTestCluster) -> None:
    config = plain_cluster.server_config(database_name=f"test_{uuid4().hex}", ssl=True)

    with pytest.raises(OperationalError, match="does not support SSL"):
        PostgresTech(config).init_db()


def test_ssl_false_connects_to_a_server_without_tls(plain_cluster: PostgresTestCluster) -> None:
    name = f"test_{uuid4().hex}"

    PostgresTech(plain_cluster.server_config(database_name=name, ssl=False)).init_db()

    assert plain_cluster.database_id(name) is not None


def test_ssl_true_creates_the_database_on_a_server_with_tls(tls_cluster: PostgresTestCluster) -> None:
    name = f"test_{uuid4().hex}"

    PostgresTech(tls_cluster.server_config(database_name=name, ssl=True)).init_db()

    assert tls_cluster.schema_exists(database=name, schema="sim_control")


@pytest.mark.parametrize("ssl", [True, False])
@pytest.mark.parametrize("generate_url", [DatabaseConfig.generate_sqlalchemy_db_url, DatabaseConfig.generate_sqlalchemy_root_url])
def test_the_connection_is_encrypted_only_if_ssl_is_set(
    tls_cluster: PostgresTestCluster,
    generate_url: Callable[[DatabaseConfig], URL],
    ssl: bool,
) -> None:
    database = tls_cluster.server_config(database_name="postgres", ssl=ssl).database

    assert _is_encrypted(generate_url(database)) is ssl
