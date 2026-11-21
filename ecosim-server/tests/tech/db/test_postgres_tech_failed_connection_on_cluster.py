from uuid import uuid4

import pytest
from ecosim_server.tech.db.postgres_tech import PostgresTech
from psycopg import sql
from sqlalchemy.exc import OperationalError
from tests.tech.db.postgres_test_cluster import PostgresTestCluster
from tests.tech.db.postgres_test_process import ROLE_THAT_DOES_NOT_EXIST

MAINTENANCE_DATABASE = "postgres"
PASSWORD = "role_password"
WRONG_PASSWORD = "wrong_password"


def _unique_name() -> str:
    return f"test_{uuid4().hex}"


@pytest.mark.parametrize("database_exists", [True, False])
def test_a_wrong_password_does_not_reach_the_maintenance_database(
    plain_cluster: PostgresTestCluster,
    database_exists: bool,
) -> None:
    role = _unique_name()
    database = _unique_name()
    plain_cluster.create_role(name=role, password=PASSWORD)
    if database_exists:
        plain_cluster.create_database(name=database, owner=role)
    config = plain_cluster.server_config(database_name=database, username=role, password=WRONG_PASSWORD)

    with pytest.raises(OperationalError, match="password authentication failed"):
        PostgresTech(config).init_db()

    assert plain_cluster.was_reached(database=database, username=role)
    assert not plain_cluster.was_reached(database=MAINTENANCE_DATABASE, username=role)


@pytest.mark.parametrize("role_pattern", ["{database}_user", "{database}-user", "user.{database}"])
def test_a_wrong_password_of_a_role_that_contains_the_database_name_does_not_reach_the_maintenance_database(
    plain_cluster: PostgresTestCluster,
    role_pattern: str,
) -> None:
    database = _unique_name()
    role = role_pattern.format(database=database)
    plain_cluster.create_role(name=role, password=PASSWORD)
    config = plain_cluster.server_config(database_name=database, username=role, password=WRONG_PASSWORD)

    with pytest.raises(OperationalError, match="password authentication failed"):
        PostgresTech(config).init_db()

    assert not plain_cluster.was_reached(database=MAINTENANCE_DATABASE, username=role)


def test_a_wrong_password_of_a_role_named_like_the_database_raises_the_original_error(plain_cluster: PostgresTestCluster) -> None:
    role = _unique_name()
    plain_cluster.create_role(name=role, password=PASSWORD)
    config = plain_cluster.server_config(database_name=role, username=role, password=WRONG_PASSWORD)

    with pytest.raises(OperationalError, match="password authentication failed"):
        PostgresTech(config).init_db()

    assert plain_cluster.database_id(role) is None


def test_a_missing_role_is_not_mistaken_for_a_missing_database(plain_cluster: PostgresTestCluster) -> None:
    config = plain_cluster.server_config(database_name=_unique_name(), username=ROLE_THAT_DOES_NOT_EXIST)

    with pytest.raises(OperationalError, match=f'role "{ROLE_THAT_DOES_NOT_EXIST}" does not exist'):
        PostgresTech(config).init_db()

    assert not plain_cluster.was_reached(database=MAINTENANCE_DATABASE, username=ROLE_THAT_DOES_NOT_EXIST)


def test_an_existing_database_without_access_raises_the_original_error_after_the_lookup(plain_cluster: PostgresTestCluster) -> None:
    role = _unique_name()
    database = _unique_name()
    plain_cluster.create_role(name=role, password=PASSWORD)
    plain_cluster.create_database(database)
    plain_cluster.execute(sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
    database_id = plain_cluster.database_id(database)

    with pytest.raises(OperationalError, match="permission denied for database"):
        PostgresTech(plain_cluster.server_config(database_name=database, username=role, password=PASSWORD)).init_db()

    assert plain_cluster.database_id(database) == database_id
    assert plain_cluster.was_reached(database=MAINTENANCE_DATABASE, username=role)
