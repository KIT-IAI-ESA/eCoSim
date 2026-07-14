import threading
from datetime import datetime
from typing import Tuple

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from integration_tests.server_client.simple_test_client import SimpleTestClient
from integration_tests.server_client.simple_test_server import generate_simple_test_server
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory


def test_three_clients_server() -> None:
    server_host = "localhost"
    server_port = 39310
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
    server = generate_simple_test_server(
        host=server_host,
        port=server_port,
        steps=steps,
        step_size_in_ms=step_size_in_ms,
        simulation_start_date=simulation_start_date,
        clients=[
            ClientSimulatorConfig(
                simulator_name="TestSimulator_1",
                model_name="TestModel_1",
                interfaces=[],
                client_id=ClientID(model_name="TestModel_1", simulator_name="TestSimulator_1"),
            ),
            ClientSimulatorConfig(
                simulator_name="TestSimulator_2",
                model_name="TestModel_2",
                interfaces=[],
                client_id=ClientID(model_name="TestModel_2", simulator_name="TestSimulator_2"),
            ),
            ClientSimulatorConfig(
                simulator_name="TestSimulator_3",
                model_name="TestModel_3",
                interfaces=[],
                client_id=ClientID(model_name="TestModel_3", simulator_name="TestSimulator_3"),
            ),
        ],
    )

    client_1 = SimpleTestClient.generate(
        communication_protocol=CommunicationProtocol.TCP_SOCKET,
        server_host=server_host,
        server_port=server_port,
        model_name="TestModel_1",
        simulator_name="TestSimulator_1",
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=_self.accumulated_step_sizes_in_seconds.value + 0.11,
                ),
            ],
        ),
    )
    client_2 = SimpleTestClient.generate(
        communication_protocol=CommunicationProtocol.TCP_SOCKET,
        server_host=server_host,
        server_port=server_port,
        model_name="TestModel_2",
        simulator_name="TestSimulator_2",
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=_self.accumulated_step_sizes_in_seconds.value + 0.22,
                ),
            ],
        ),
    )
    client_3 = SimpleTestClient.generate(
        communication_protocol=CommunicationProtocol.TCP_SOCKET,
        server_host=server_host,
        server_port=server_port,
        model_name="TestModel_3",
        simulator_name="TestSimulator_3",
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface",
                    value=_self.accumulated_step_sizes_in_seconds.value + 0.33,
                ),
            ],
        ),
    )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    client_1.start()
    client_2.start()
    client_3.start()

    server_thread.join()

    repositories = server.repositories

    client_1_measurement_repository = repositories.measurement_repository(client_id=client_1._client_config.client_id())
    if not isinstance(client_1_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_1_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        assert (timestamp - simulation_start_date).total_seconds() + 0.11 == values[0].value
        return (timestamp - simulation_start_date).total_seconds() + 0.11 == values[0].value

    (client_1_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_1_records))

    client_2_measurement_repository = repositories.measurement_repository(client_id=client_2._client_config.client_id())
    if not isinstance(client_2_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_2_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        assert (timestamp - simulation_start_date).total_seconds() + 0.22 == values[0].value
        return (timestamp - simulation_start_date).total_seconds() + 0.22 == values[0].value

    (client_2_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_2_records))

    client_3_measurement_repository = repositories.measurement_repository(client_id=client_3._client_config.client_id())
    if not isinstance(client_3_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_3_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        assert (timestamp - simulation_start_date).total_seconds() + 0.33 == values[0].value
        return (timestamp - simulation_start_date).total_seconds() + 0.33 == values[0].value

    (client_3_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_3_records))
