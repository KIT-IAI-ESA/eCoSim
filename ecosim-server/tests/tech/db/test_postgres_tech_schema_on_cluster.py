from uuid import uuid4

import pytest
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_server.tech.db.postgres_tech import PostgresTech
from psycopg import sql
from tests.data.generate_postgres_name_config import generate_simulation_config
from tests.tech.db.postgres_test_cluster import PostgresTestCluster

TABLE_QUERY = "SELECT 1 FROM information_schema.tables WHERE table_schema = 'sim_control' AND table_name = %s"


def _database_with_a_schema_of_an_earlier_run(cluster: PostgresTestCluster) -> str:
    name = f"test_{uuid4().hex}"
    cluster.create_database(name)
    cluster.execute(statement=sql.SQL("CREATE SCHEMA sim_control"), database=name)
    cluster.execute(statement=sql.SQL("CREATE TABLE sim_control.marker (content text)"), database=name)
    return name


def test_an_existing_schema_without_the_flag_raises_and_keeps_its_tables(plain_cluster: PostgresTestCluster) -> None:
    name = _database_with_a_schema_of_an_earlier_run(plain_cluster)

    with pytest.raises(RuntimeError, match="already exists"):
        PostgresTech(plain_cluster.server_config(database_name=name)).init_db()

    assert plain_cluster.fetch_value(query=TABLE_QUERY, parameter="marker", database=name) is not None


def test_an_existing_schema_fails_with_the_options_to_go_on(plain_cluster: PostgresTestCluster) -> None:
    name = _database_with_a_schema_of_an_earlier_run(plain_cluster)

    with pytest.raises(RuntimeError) as error_info:
        PostgresTech(plain_cluster.server_config(database_name=name)).init_db()

    assert str(error_info.value) == (
        "Schema 'sim_control' already exists from an earlier run. Use --database-schema NAME for another schema or "
        + "--database-drop-existing-schema to delete the old results. Use --restore-simulation-run to continue that run. "
        + "With ecosim run, the first two go after --."
    )


def test_an_existing_schema_with_the_flag_is_dropped_and_recreated(plain_cluster: PostgresTestCluster) -> None:
    name = _database_with_a_schema_of_an_earlier_run(plain_cluster)

    PostgresTech(plain_cluster.server_config(database_name=name, drop_existing_schema=True)).init_db()

    assert plain_cluster.schema_exists(database=name, schema="sim_control")
    assert plain_cluster.fetch_value(query=TABLE_QUERY, parameter="marker", database=name) is None


@pytest.mark.parametrize("drop_existing_schema", [False, True])
def test_a_restore_keeps_the_tables_of_an_existing_schema_with_and_without_the_flag(
    plain_cluster: PostgresTestCluster,
    drop_existing_schema: bool,
) -> None:
    name = _database_with_a_schema_of_an_earlier_run(plain_cluster)

    RepositoriesDB.create(
        server_config=plain_cluster.server_config(database_name=name, drop_existing_schema=drop_existing_schema),
        simulation_config=generate_simulation_config(clients=[], restore=True),
    )

    assert plain_cluster.fetch_value(query=TABLE_QUERY, parameter="marker", database=name) is not None
