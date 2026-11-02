from __future__ import annotations

import threading
from datetime import datetime
from typing import List

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.simulation.state.simulation_state import SimulationState
from integration_tests.test_data.server_client.server_thread import assert_server_finishes_in_time
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import (
    SimpleTestServer,
    SimpleTestServerParameters,
    generate_simple_test_server,
)
from integration_tests.test_data.test_client_data import TestClientData

STEPS = 5
STEP_SIZE_IN_MS = 2_500
OUTPUT_INTERFACE = "Interface_Output"
SIMULATION_START_DATE = datetime(year=2025, month=1, day=1)


def test_the_predefined_client_server_run_is_stored_by_every_repository(
    database_config: DatabaseConfig,
    communication_protocol: CommunicationProtocol,
) -> None:
    """Runs the same single client simulation on every 'Repositories' implementation and reads its results back."""
    client_data = _client_data(database_config, communication_protocol)
    server_port = get_free_port()
    server = _server(database_config, communication_protocol, client_data, server_port)
    client = _client(communication_protocol, server_port, client_data)

    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    client.start()

    assert_server_finishes_in_time(server_thread)
    _assert_measurements_of(server, client_data)
    assert server.simulation_state_repository().current() is SimulationState.FINISHED


def _client_data(
    database_config: DatabaseConfig,
    communication_protocol: CommunicationProtocol,
) -> TestClientData:
    client_data = TestClientData(
        simulator_name=f"RepositorySimulator_{database_config.type.value}_{communication_protocol.name}",
        model_name="RepositoryModel",
        interfaces=[],
    )
    client_data.add_interface(
        interface_name=OUTPUT_INTERFACE,
        unit="float64",
        interface_type=InterfaceType.OUTPUT,
    )
    return client_data


def _server(
    database_config: DatabaseConfig,
    communication_protocol: CommunicationProtocol,
    client_data: TestClientData,
    server_port: int,
) -> SimpleTestServer:
    return generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host="localhost",
            port=server_port,
            steps=STEPS,
            step_size_in_ms=STEP_SIZE_IN_MS,
            simulation_start_date=SIMULATION_START_DATE,
            clients=[client_data.to_client_simulator_config()],
            database_config=database_config,
        ),
    )


def _client(
    communication_protocol: CommunicationProtocol,
    server_port: int,
    client_data: TestClientData,
) -> SimpleTestClient:
    return SimpleTestClient.of_test_data(
        communication_protocol=communication_protocol,
        server_host="localhost",
        server_port=server_port,
        test_client_data=client_data,
        on_simulation_step_return=lambda _self, received_inputs, steps: ClientSimStepData(
            interface_values=[
                client_data.interface_protocol_value_of(
                    interface_name=OUTPUT_INTERFACE,
                    value=_self.accumulated_step_sizes_in_seconds.value,
                ),
            ],
        ),
    )


def _assert_measurements_of(
    server: SimpleTestServer,
    client_data: TestClientData,
) -> None:
    entries: List[MeasurementEntry] = sorted(
        server.measurement_repository(client_id=client_data.to_client_simulator_config().client_id).all(),
        key=lambda entry: entry.timestamp,
    )

    assert len(entries) == STEPS, f"Expected {STEPS} entries, got {len(entries)}"
    for step, entry in enumerate(entries):
        expected_value = (step + 1) * STEP_SIZE_IN_MS / 1000
        assert _output_value_of(entry) == expected_value, f"failed at step {step}: {_output_value_of(entry)} != {expected_value}"
    _assert_timestamps_are_one_step_apart(entries)


def _assert_timestamps_are_one_step_apart(entries: List[MeasurementEntry]) -> None:
    for previous_entry, entry in zip(entries, entries[1:]):
        distance_in_ms = (entry.timestamp - previous_entry.timestamp).total_seconds() * 1000
        assert distance_in_ms == STEP_SIZE_IN_MS, f"Expected the entries to be {STEP_SIZE_IN_MS}ms apart, got {distance_in_ms}ms"


def _output_value_of(entry: MeasurementEntry) -> float | None:
    for value in entry.values:
        if value.name == OUTPUT_INTERFACE and isinstance(value.value, (float, int)):
            return float(value.value)
    return None
