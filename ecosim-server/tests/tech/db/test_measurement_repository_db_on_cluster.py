from __future__ import annotations

from uuid import uuid4

import pytest
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.tech.one_line_errors import one_line_message
from ecosim_server.data.repositories import create_repositories
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_server.tech.db.postgres_tech import PostgresTech
from psycopg import sql
from tests.data.generate_postgres_name_config import generate_client_simulator_config, generate_simulation_config
from tests.tech.db.postgres_test_cluster import PostgresTestCluster


def test_remove_starting_at_keeps_only_the_earlier_measurements(plain_cluster: PostgresTestCluster) -> None:
    simulator = generate_client_simulator_config(simulator_name="removal_test", interfaces=[("T_room", InterfaceType.OUTPUT)])
    config = generate_simulation_config(clients=[simulator])
    server_config = plain_cluster.server_config(database_name=f"test_{uuid4().hex}")
    repositories = RepositoriesDB.create(server_config=server_config, simulation_config=config)
    repository = repositories.measurement_repository(client_id=simulator.client_id)
    for step in range(4):
        repository.add(values=(ProtocolInterfaceValue(name="T_room", value=293.15),), timestamp=config.date_time_for_step(step))

    repository.remove_starting_at(timestamp=config.date_time_for_step(2))

    assert [config.date_time_to_step(entry.timestamp) for entry in repository.all()] == [0, 1]


def test_a_measurement_table_that_cannot_be_created_stops_the_start_with_a_one_line_error(plain_cluster: PostgresTestCluster) -> None:
    simulator = generate_client_simulator_config(simulator_name="blocked_table_test")
    server_config = plain_cluster.server_config(database_name=f"test_{uuid4().hex}")
    PostgresTech(server_config).init_db()
    # PostgreSQL creates no table that has the name of a type
    plain_cluster.execute(
        statement=sql.SQL("CREATE TYPE {}.module_blocked_table_test AS ENUM ()").format(sql.Identifier(server_config.database.schema)),
        database=server_config.database.name,
    )

    with pytest.raises(RuntimeError) as error_info:
        create_repositories(server_config=server_config, simulation_config=generate_simulation_config(clients=[simulator], restore=True))

    message = one_line_message(error=error_info.value)
    assert message.startswith(f"Cannot create the PostgreSQL table {server_config.database.schema}.module_blocked_table_test: ")
    assert "\n" not in message
