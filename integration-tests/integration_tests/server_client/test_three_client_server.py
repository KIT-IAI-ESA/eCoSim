from datetime import datetime
from typing import Tuple

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.tech.port_utils import get_free_port
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import (
    SimpleTestServer,
    SimpleTestServerParameters,
    generate_simple_test_server,
)
from integration_tests.test_data.test_client_data import TestClientData


def test_three_clients_server(communication_protocol: CommunicationProtocol) -> None:
    run_three_clients_server(communication_protocol)


def run_three_clients_server(communication_protocol: CommunicationProtocol) -> SimpleTestServer:
    server_host = "localhost"
    server_port = get_free_port()
    steps = 10
    step_size_in_ms = 2_500
    simulation_start_date: datetime = datetime(
        year=2025,
        month=1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    client_data_1 = TestClientData.with_output(simulator_name="TestSimulator_1", model_name="TestModel_1", output_name="TestInterface")
    client_data_2 = TestClientData.with_output(simulator_name="TestSimulator_2", model_name="TestModel_2", output_name="TestInterface")
    client_data_3 = TestClientData.with_output(simulator_name="TestSimulator_3", model_name="TestModel_3", output_name="TestInterface")
    server = generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host=server_host,
            port=server_port,
            steps=steps,
            step_size_in_ms=step_size_in_ms,
            simulation_start_date=simulation_start_date,
            clients=[
                client_data_1.to_client_simulator_config(),
                client_data_2.to_client_simulator_config(),
                client_data_3.to_client_simulator_config(),
            ],
        ),
    )

    client_1 = SimpleTestClient.of_test_data(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        test_client_data=client_data_1,
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=_self.accumulated_step_sizes_in_seconds.value + 0.11,
                ),
            ],
        ),
    )
    client_2 = SimpleTestClient.of_test_data(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        test_client_data=client_data_2,
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=_self.accumulated_step_sizes_in_seconds.value + 0.22,
                ),
            ],
        ),
    )
    client_3 = SimpleTestClient.of_test_data(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        test_client_data=client_data_3,
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=_self.accumulated_step_sizes_in_seconds.value + 0.33,
                ),
            ],
        ),
    )

    server.start_in_thread()

    server.wait_until_listening()
    client_1.start()
    client_2.start()
    client_3.start()

    server.assert_finishing_in_time()
    server.print_measurement_statistics()

    client_1_measurement_repository = server.measurement_repository(client_id=client_1.client_id)
    if not isinstance(client_1_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_1_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        assert (timestamp - simulation_start_date).total_seconds() + 0.11 == values[0].value
        return (timestamp - simulation_start_date).total_seconds() + 0.11 == values[0].value

    (client_1_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_1_records))

    client_2_measurement_repository = server.measurement_repository(client_id=client_2.client_id)
    if not isinstance(client_2_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_2_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        assert (timestamp - simulation_start_date).total_seconds() + 0.22 == values[0].value
        return (timestamp - simulation_start_date).total_seconds() + 0.22 == values[0].value

    (client_2_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_2_records))

    client_3_measurement_repository = server.measurement_repository(client_id=client_3.client_id)
    if not isinstance(client_3_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_3_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        assert (timestamp - simulation_start_date).total_seconds() + 0.33 == values[0].value
        return (timestamp - simulation_start_date).total_seconds() + 0.33 == values[0].value

    (client_3_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_3_records))

    return server
