from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Tuple

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.simulation.state.simulation_state import SimulationState
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import (
    SimpleTestServer,
    SimpleTestServerParameters,
    generate_simple_test_server,
)
from integration_tests.test_data.test_client_data import TestClientData

STEPS = 6
STEP_SIZE_IN_MS = 2_500
OUTPUT_INTERFACE = "Interface_Output"


# TODO: a PostgreSQL test that a restore keeps what an earlier server stored, this one stores the steps after the server set up its schema
def test_a_restore_after_an_uneven_abort_continues_from_the_replayed_steps_and_stores_every_step_once(
    database_config: DatabaseConfig,
    communication_protocol: CommunicationProtocol,
) -> None:
    run_name = f"{database_config.type.value}_{communication_protocol.name}"
    ahead, behind = _client_data(simulator_name=f"RestoreAhead_{run_name}"), _client_data(simulator_name=f"RestoreBehind_{run_name}")
    server_port = get_free_port()
    server = _restoring_server(
        database_config=database_config,
        communication_protocol=communication_protocol,
        clients_data=[ahead, behind],
        server_port=server_port,
    )
    _store_steps_of_the_aborted_run(server=server, client_data=ahead, steps=4)
    _store_steps_of_the_aborted_run(server=server, client_data=behind, steps=2)

    server.start_in_thread()
    server.wait_until_listening()
    for client_data in (ahead, behind):
        SimpleTestClient.sending_accumulated_step_sizes(
            communication_protocol=communication_protocol,
            server_host="localhost",
            server_port=server_port,
            test_client_data=client_data,
            interface_name=OUTPUT_INTERFACE,
        ).start()

    server.assert_finishing_in_time()
    assert server.simulation_state_repository().current() is SimulationState.FINISHED
    # the clients send their accumulated step sizes, so a step after the restart only has the right value if the batch was replayed
    expected = [(step, _accumulated_step_sizes_in_seconds_after(step)) for step in range(STEPS)]
    assert [_stored_steps_and_values(server=server, client_data=ahead), _stored_steps_and_values(server=server, client_data=behind)] == [expected] * 2


def _client_data(simulator_name: str) -> TestClientData:
    client_data = TestClientData(simulator_name=simulator_name, model_name="RestoreModel", interfaces=[])
    client_data.add_interface(interface_name=OUTPUT_INTERFACE, unit="float64", interface_type=InterfaceType.OUTPUT)
    return client_data


def _restoring_server(
    database_config: DatabaseConfig,
    communication_protocol: CommunicationProtocol,
    clients_data: List[TestClientData],
    server_port: int,
) -> SimpleTestServer:
    return generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host="localhost",
            port=server_port,
            steps=STEPS,
            step_size_in_ms=STEP_SIZE_IN_MS,
            # with a time zone, so PostgreSQL timestamps map to the same steps
            simulation_start_date=datetime(year=2025, month=1, day=1, tzinfo=timezone.utc),
            clients=[client_data.to_client_simulator_config() for client_data in clients_data],
            database_config=database_config,
            restore_simulation_run=True,
        ),
    )


def _store_steps_of_the_aborted_run(
    server: SimpleTestServer,
    client_data: TestClientData,
    steps: int,
) -> None:
    repository = server.measurement_repository(client_id=client_data.to_client_simulator_config().client_id)
    for step in range(steps):
        output_value = client_data.interface_protocol_value_of(interface_name=OUTPUT_INTERFACE, value=_accumulated_step_sizes_in_seconds_after(step))
        repository.add(values=(output_value,), timestamp=server.step_to_date(step))


def _accumulated_step_sizes_in_seconds_after(step: int) -> float:
    return (step + 1) * STEP_SIZE_IN_MS / 1000


def _stored_steps_and_values(
    server: SimpleTestServer,
    client_data: TestClientData,
) -> List[Tuple[int, InterfaceValue]]:
    entries = server.measurement_repository(client_id=client_data.to_client_simulator_config().client_id).all()
    return [(server.date_to_step(entry.timestamp), entry.values[0].value) for entry in sorted(entries, key=lambda entry: entry.timestamp)]
