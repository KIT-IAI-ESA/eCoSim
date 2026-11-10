from uuid import uuid4

from ecosim_server.config.server_config import ServerConfig
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_server.simulation.state.simulation_state_repository_db import SimulationStateDTO
from ecosim_server.tech.db.postgres_tech import PostgresTech
from ecosim_server.tech.db.server_time_measurement_repository_db import ServerTimeMeasurementDBEntry
from psycopg import sql
from tests.data.generate_postgres_name_config import generate_client_simulator_config, generate_simulation_config
from tests.tech.db.postgres_test_cluster import PostgresTestCluster, skip_in_ci

pytestmark = skip_in_ci

SCHEMA = "configured_schema"


def _config_of_a_new_database(cluster: PostgresTestCluster) -> ServerConfig:
    return cluster.server_config(database_name=f"test_{uuid4().hex}", schema=SCHEMA)


def test_the_tables_of_a_run_are_created_in_the_configured_schema(plain_cluster: PostgresTestCluster) -> None:
    config = _config_of_a_new_database(plain_cluster)
    simulator = generate_client_simulator_config(simulator_name="schema_test")
    repositories = RepositoriesDB.create(server_config=config, simulation_config=generate_simulation_config(clients=[simulator]))

    repositories.measurement_repository(simulator.client_id)

    for table in [SimulationStateDTO.__tablename__, ServerTimeMeasurementDBEntry.__tablename__, "module_schema_test"]:
        assert plain_cluster.table_exists(database=config.database.name, schema=SCHEMA, table=table)


def test_a_table_in_the_configured_schema_is_found(plain_cluster: PostgresTestCluster) -> None:
    config = _config_of_a_new_database(plain_cluster)
    PostgresTech(config).init_db()
    plain_cluster.execute(statement=sql.SQL(f"CREATE TABLE {SCHEMA}.marker (content text)"), database=config.database.name)

    assert PostgresTech(config).db_connection().table_exists("marker")
