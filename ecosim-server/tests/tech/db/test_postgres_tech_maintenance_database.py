from typing import Any
from uuid import uuid4

import pytest
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.tech.db import postgres_tech
from ecosim_server.tech.db.postgres_tech import PostgresTech
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import OperationalError, ProgrammingError
from tests.tech.db.postgres_test_cluster import PostgresTestCluster, skip_in_ci

pytestmark = skip_in_ci

MAINTENANCE_DATABASE = "postgres"
PASSWORD = "role_password"


def _new_role(
    cluster: PostgresTestCluster,
    can_create_databases: bool = True,
) -> str:
    name = f"test_{uuid4().hex}"
    cluster.create_role(name=name, password=PASSWORD, can_create_databases=can_create_databases)
    return name


def _config_of(
    cluster: PostgresTestCluster,
    role: str,
) -> ServerConfig:
    return cluster.server_config(database_name=role, username=role, password=PASSWORD)


def test_an_existing_database_does_not_touch_the_maintenance_database(plain_cluster: PostgresTestCluster) -> None:
    role = _new_role(plain_cluster)
    plain_cluster.create_database(name=role, owner=role)

    PostgresTech(_config_of(plain_cluster, role=role)).init_db()

    assert plain_cluster.schema_exists(database=role, schema="sim_control")
    assert not plain_cluster.was_reached(database=MAINTENANCE_DATABASE, username=role)


def test_an_existing_database_works_for_a_role_rejected_on_the_maintenance_database(plain_cluster: PostgresTestCluster) -> None:
    role = _new_role(plain_cluster)
    plain_cluster.create_database(name=role, owner=role)
    plain_cluster.reject_on_maintenance_database(role)

    PostgresTech(_config_of(plain_cluster, role=role)).init_db()

    assert plain_cluster.schema_exists(database=role, schema="sim_control")


def test_a_missing_database_shows_the_real_error_for_a_role_rejected_on_the_maintenance_database(plain_cluster: PostgresTestCluster) -> None:
    role = _new_role(plain_cluster)
    plain_cluster.reject_on_maintenance_database(role)

    with pytest.raises(OperationalError, match="does not exist") as error:
        PostgresTech(_config_of(plain_cluster, role=role)).init_db()

    assert "pg_hba.conf rejects connection" in str(error.value.__cause__)
    assert plain_cluster.database_id(role) is None


def test_a_missing_database_shows_the_real_error_for_a_role_that_cannot_create_one(plain_cluster: PostgresTestCluster) -> None:
    role = _new_role(plain_cluster, can_create_databases=False)

    with pytest.raises(ProgrammingError, match="permission denied to create database"):
        PostgresTech(_config_of(plain_cluster, role=role)).init_db()

    assert plain_cluster.database_id(role) is None


def test_a_missing_database_is_created_through_the_maintenance_database(plain_cluster: PostgresTestCluster) -> None:
    role = _new_role(plain_cluster)

    PostgresTech(_config_of(plain_cluster, role=role)).init_db()

    assert plain_cluster.database_id(role) is not None
    assert plain_cluster.was_reached(database=MAINTENANCE_DATABASE, username=role)


@pytest.mark.parametrize("database_exists", [True, False])
def test_init_db_leaves_no_connection_open(
    plain_cluster: PostgresTestCluster,
    monkeypatch: pytest.MonkeyPatch,
    database_exists: bool,
) -> None:
    engines: list[Engine] = []

    def create_engine_and_keep_it(*arguments: Any, **keyword_arguments: Any) -> Engine:
        engines.append(create_engine(*arguments, **keyword_arguments))
        return engines[-1]

    monkeypatch.setattr(postgres_tech, "create_engine", create_engine_and_keep_it)
    role = _new_role(plain_cluster)
    if database_exists:
        plain_cluster.create_database(name=role, owner=role)

    PostgresTech(_config_of(plain_cluster, role=role)).init_db()

    assert engines
    assert plain_cluster.has_no_connections(role)
