from __future__ import annotations

from uuid import uuid4

from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_server.data.repositories_db import RepositoriesDB
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
