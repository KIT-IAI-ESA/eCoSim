from datetime import datetime
from typing import Any, Generator

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.port_utils import get_free_port

from ecosim_test_common.test_data.server_client.pre_set_two_clients import PreSetTwoClientsData
from ecosim_test_common.test_data.server_client.simple_test_client import SimpleTestClient
from ecosim_test_common.test_data.server_client.simple_test_server import generate_simple_test_server, SimpleTestServerParameters
from ecosim_test_common.test_data.test_client_data import TestClientData


@pytest.fixture(
    scope="function",
    autouse=False,
)
def pre_set_two_clients(communication_protocol: CommunicationProtocol) -> Generator[PreSetTwoClientsData, Any, None]:
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

    client_data_1 = TestClientData(
        simulator_name="Simulator_1",
        model_name="Model_1",
        interfaces=[],
    )
    client_1_input_interface = client_data_1.add_interface(
        interface_name="Interface_Input_1",
        unit="float64_matrix",
        interface_type=InterfaceType.INPUT,
    )
    client_data_1.add_interface(
        interface_name="Interface_Output_1",
        unit="float64_matrix",
        interface_type=InterfaceType.OUTPUT,
    )

    client_data_2 = TestClientData(
        simulator_name="Simulator_2",
        model_name="Model_2",
        interfaces=[],
    )
    client_data_2.add_interface(
        interface_name="Interface_Output_2",
        unit="float64_matrix",
        interface_type=InterfaceType.OUTPUT,
        connected_interface=client_1_input_interface,
    )

    server = generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host=server_host,
            port=server_port,
            steps=steps,
            step_size_in_ms=step_size_in_ms,
            simulation_start_date=simulation_start_date,
            restore_simulation_run=False,
            clients=[
                client_data_1.to_client_simulator_config(),
                client_data_2.to_client_simulator_config(),
            ],
        ),
    )

    def client_1_on_simulation_step(
        client: SimpleTestClient,
        received_inputs: dict[InterfaceId, InterfaceValueType],
        steps: float,
    ) -> ClientSimStepData:
        received_value = received_inputs.get(
            client_1_input_interface.interface_name,
            None,
        )
        if received_value is None or not (isinstance(received_value, float) or isinstance(received_value, int)):
            raise RuntimeError(
                f"Missing input interface '{client_1_input_interface.interface_name}' or value None | value: {received_value}",
            )
        return ClientSimStepData(
            interface_values=[
                client_data_1.interface_protocol_value_of(
                    "Interface_Output_1",
                    client.accumulated_step_sizes_in_seconds.value + received_value,
                ),
            ],
        )

    client_1 = SimpleTestClient.of_test_data(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        test_client_data=client_data_1,
        on_simulation_step_return=client_1_on_simulation_step,
    )
    client_2 = SimpleTestClient.of_test_data(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        test_client_data=client_data_2,
        on_simulation_step_return=lambda _self, received_inputs, step_size_in_seconds: ClientSimStepData(
            interface_values=[
                client_data_2.interface_protocol_value_of(
                    "Interface_Output_2",
                    -_self.accumulated_step_sizes_in_seconds.value * 10_000,
                ),
            ],
        ),
    )

    yield PreSetTwoClientsData(
        client_1=client_1,
        client_2=client_2,
        server=server,
        step_size_in_ms=step_size_in_ms,
        steps=steps,
        start_date=simulation_start_date,
        client_1_data=client_data_1,
        client_2_data=client_data_2,
    )
