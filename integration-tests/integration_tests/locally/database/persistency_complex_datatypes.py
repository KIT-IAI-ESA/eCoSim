import os
import threading
from typing import Any, Generator

import psycopg2
import pytest
from psycopg2 import sql
from psycopg2._psycopg import connection
from psycopg2.extras import DictCursor
from testcontainers.postgres import PostgresContainer

from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue, InterfaceValueType
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from integration_tests.server_client.simple_test_client import SimpleTestClient
from integration_tests.server_client.simple_test_server import generate_simple_test_server, RepositoryType

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


@pytest.fixture(scope="function", autouse=True)
def postgres_container() -> Generator[PostgresContainer, Any, None]:
    container = (
        PostgresContainer("postgres:16-alpine", port=5432)
        .with_bind_ports(5432, 5432)
        .with_name("persistence_db")
    )

    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="function", autouse=True)
def db_connection(postgres_container: PostgresContainer) -> Generator[connection, Any, None]:
    conn = psycopg2.connect(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        database=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password,
        cursor_factory=DictCursor,
    )
    yield conn
    conn.close()


def test_db_persistence_float(
    postgres_container: PostgresContainer,
    db_connection: connection,
) -> None:
    server = generate_simple_test_server(
        host="localhost",
        port=6543,
        repository_type=RepositoryType.DB,
        steps=10,
        database_config=DatabaseConfig(
            host=postgres_container.get_container_host_ip(),
            port=postgres_container.get_exposed_port(5432),
            ssl=False,
            drop_existing_schema=True,
            username=postgres_container.username,
            password=postgres_container.password,
            schema="postgres",
            name=postgres_container.dbname,
        ),
        clients=[
            ClientSimulatorConfig(
                simulator_name="TestSimulator",
                model_name="TestModel",
                client_id=ClientID(model_name="TestModel", simulator_name="TestSimulator"),
                interfaces=[
                    ModelInterfaceServer(
                        SimulatorInterfaceId(
                            simulator_name="TestSimulator",
                            model_interface_id=ModelInterfaceId(
                                model_name="TestModel",
                                interface="TestInterface",
                            ),
                        ),
                        name="TestInterface",
                        unit="TestUnit",
                        description=None,
                        interface_type=InterfaceType.OUTPUT,
                        required=True,
                        connected_to=[],
                    ),
                ],
            ),
        ],
    )

    client = SimpleTestClient.generate(
        server_host="localhost",
        server_port=6543,
        model_name="TestModel",
        simulator_name="TestSimulator",
        interface_config=ClientInterfaceConfig(
            interfaces=[
                ModelInterfaceClient(
                    model_interface_id=ModelInterfaceId(
                        model_name="TestModel",
                        interface="TestInterface",
                    ),
                    type=InterfaceType.OUTPUT,
                    name="TestInterface",
                    required=True,
                    description="TestDescription",
                    unit="TestUnit",
                ),
            ],
        ),
        on_simulation_step_return=lambda _self,
                                         received_inputs,
                                         current_step: ClientSimStepData([ProtocolInterfaceValue(name="TestInterface", value=2.5)]),
    )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    client.start()

    server_thread.join()

    cursor = db_connection.cursor()
    cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier("postgres")))

    cursor.execute("SELECT * FROM module_testsimulator")
    rows = cursor.fetchall()

    for row in rows:
        assert row['o_testinterface'] == 2.5
        assert row['o_testinterface_json'] is None

    cursor.close()


def test_db_persistence_matrix(
    postgres_container: PostgresContainer,
    db_connection: connection,
) -> None:
    matrix: InterfaceValueType = [
        [1.1, 2.2, 3.3],
        [4.4, 5.5, 6.6],
        [7.7, 8.8, 9.9],
    ]

    server = generate_simple_test_server(
        host="localhost",
        port=6543,
        repository_type=RepositoryType.DB,
        steps=10,
        database_config=DatabaseConfig(
            host=postgres_container.get_container_host_ip(),
            port=postgres_container.get_exposed_port(5432),
            ssl=False,
            drop_existing_schema=True,
            username=postgres_container.username,
            password=postgres_container.password,
            schema="postgres",
            name=postgres_container.dbname,
        ),
        clients=[
            ClientSimulatorConfig(
                simulator_name="TestSimulator",
                model_name="TestModel",
                client_id=ClientID(model_name="TestModel", simulator_name="TestSimulator"),
                interfaces=[
                    ModelInterfaceServer(
                        SimulatorInterfaceId(
                            simulator_name="TestSimulator",
                            model_interface_id=ModelInterfaceId(
                                model_name="TestModel",
                                interface="TestInterface",
                            ),
                        ),
                        name="TestInterface",
                        unit="TestUnit",
                        description=None,
                        interface_type=InterfaceType.OUTPUT,
                        required=True,
                        connected_to=[],
                    ),
                ],
            ),
        ],
    )

    client = SimpleTestClient.generate(
        server_host="localhost", server_port=6543,
        model_name="TestModel",
        simulator_name="TestSimulator",
        interface_config=ClientInterfaceConfig(
            interfaces=[
                ModelInterfaceClient(
                    model_interface_id=ModelInterfaceId(
                        model_name="TestModel",
                        interface="TestInterface",
                    ),
                    type=InterfaceType.OUTPUT,
                    name="TestInterface",
                    required=True,
                    description="TestDescription",
                    unit="TestUnit",
                ),
            ],
        ),
        on_simulation_step_return=lambda _self,
                                         received_inputs,
                                         current_step: ClientSimStepData([ProtocolInterfaceValue(name="TestInterface", value=matrix)]),
    )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    client.start()

    server_thread.join()

    cursor = db_connection.cursor()
    cursor.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier("postgres")))

    cursor.execute("SELECT * FROM module_testsimulator")
    rows = cursor.fetchall()

    for row in rows:
        assert row['o_testinterface'] is None
        assert row['o_testinterface_json'] == matrix

    cursor.close()
