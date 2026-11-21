from pathlib import Path
from uuid import uuid4

import pytest
from ecosim_common.config.db_config_overwrite import DbConfigOverwrite
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.tech.db.postgres_tech import PostgresTech
from psycopg import sql
from sqlalchemy.exc import OperationalError
from tests.data.generate_server_config import write_server_config_file
from tests.tech.db.postgres_test_cluster import PostgresTestCluster
from tests.tech.db.postgres_test_process import HOST
from tests.tech.db.special_passwords import PASSWORD_PARTS, PASSWORD_WITH_PARTS, SPECIAL_PASSWORDS


def _unique_name() -> str:
    return f"test_{uuid4().hex}"


def test_a_missing_database_is_created(plain_cluster: PostgresTestCluster) -> None:
    name = _unique_name()
    assert plain_cluster.database_id(name) is None

    PostgresTech(plain_cluster.server_config(database_name=name)).init_db()

    assert plain_cluster.database_id(name) is not None
    assert plain_cluster.schema_exists(database=name, schema="sim_control")


@pytest.mark.parametrize("name", ["Mixed_Case_Name", "name-with-dash", 'name"with"quotes', "name with space", "a%b", "x-:b"])
def test_a_missing_database_with_a_name_that_needs_quoting_is_created(
    plain_cluster: PostgresTestCluster,
    name: str,
) -> None:
    PostgresTech(plain_cluster.server_config(database_name=name)).init_db()

    assert plain_cluster.database_id(name) is not None
    assert plain_cluster.schema_exists(database=name, schema="sim_control")


def test_an_existing_database_is_left_alone(plain_cluster: PostgresTestCluster) -> None:
    name = _unique_name()
    plain_cluster.create_database(name)
    plain_cluster.execute(statement=sql.SQL("CREATE TABLE marker AS SELECT 'kept' AS content"), database=name)
    database_id = plain_cluster.database_id(name)

    PostgresTech(plain_cluster.server_config(database_name=name)).init_db()

    assert plain_cluster.database_id(name) == database_id
    assert plain_cluster.fetch_value(query="SELECT content FROM marker WHERE content = %s", parameter="kept", database=name) == "kept"


def test_an_existing_database_does_not_need_the_right_to_create_one(plain_cluster: PostgresTestCluster) -> None:
    name = _unique_name()
    plain_cluster.create_role(name=name, password="role_password", can_create_databases=False)
    plain_cluster.create_database(name=name, owner=name)

    PostgresTech(plain_cluster.server_config(database_name=name, username=name, password="role_password")).init_db()

    assert plain_cluster.schema_exists(database=name, schema="sim_control")


@pytest.mark.parametrize("password", SPECIAL_PASSWORDS)
def test_a_password_with_special_characters_from_the_config_file_connects(
    plain_cluster: PostgresTestCluster,
    tmp_path: Path,
    password: str,
) -> None:
    name = _unique_name()
    plain_cluster.create_role(name=name, password=password)
    config = ServerConfig.of_file(
        file=write_server_config_file(directory=tmp_path, host=HOST, port=plain_cluster.port, username=name, password=password),
        db_config_overwrite=DbConfigOverwrite(_name=name, _schema="postgres"),
    )

    PostgresTech(config).init_db()
    PostgresTech(config).db_connection()

    assert plain_cluster.schema_exists(database=name, schema="postgres")


def test_a_wrong_password_does_not_show_any_part_of_it(plain_cluster: PostgresTestCluster) -> None:
    config = plain_cluster.server_config(database_name="postgres", password=PASSWORD_WITH_PARTS)

    with pytest.raises(OperationalError, match="password authentication failed") as error:
        PostgresTech(config).init_db()

    for part in PASSWORD_PARTS:
        assert part not in str(error.value)
