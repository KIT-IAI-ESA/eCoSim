import dataclasses
import threading
from datetime import datetime
from typing import Any, Generator, Tuple

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType, ProtocolInterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from integration_tests.server_client.simple_test_client import SimpleTestClient
from integration_tests.server_client.simple_test_server import SimpleTestServer, SimpleTestServerParameters, generate_simple_test_server
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from integration_tests.test_data.test_client_data import TestClientData


@dataclasses.dataclass
class PreSetTwoClientsData:
    client_1: SimpleTestClient
    client_2: SimpleTestClient
    server: SimpleTestServer
    step_size_in_ms: int
    steps: int
    start_date: datetime
    client_1_data: TestClientData
    client_2_data: TestClientData

    def measurement_repository_client_1(self) -> MeasurementRepository:
        return self.server.measurement_repository(client_id=self.client_1.client_id)

    def measurement_repository_client_2(self) -> MeasurementRepository:
        return self.server.measurement_repository(client_id=self.client_2.client_id)

    def client_2_output_value_at_step(self, step: int) -> float:
        return -(step + 1) * self.step_size_in_seconds * 10_000

    def client_1_output_value_at_step(self, step: int) -> float:
        return (step + 1) * self.step_size_in_seconds + self.client_2_output_value_at_step(step)

    def add_client_1_measurement(
        self,
        step: int,
        input_value: float,
        output_value: float,
    ) -> None:
        self.measurement_repository_client_1().add(
            values=(
                self.client_1_data.interface_protocol_value_of(
                    interface_name="Interface_Output_1",
                    value=output_value,
                ),
                self.client_1_data.interface_protocol_value_of(
                    interface_name="Interface_Input_1",
                    value=input_value,
                ),
            ),
            timestamp=self._step_to_date(step),
        )

    def add_client_2_measurement(
        self,
        step: int,
        output_value: float,
    ) -> None:
        self.measurement_repository_client_2().add(
            values=(
                self.client_2_data.interface_protocol_value_of(
                    interface_name="Interface_Output_2",
                    value=output_value,
                ),
            ),
            timestamp=self._step_to_date(step),
        )

    def _step_to_date(self, step: int) -> datetime:
        return self.server.step_to_date(step)

    def date_to_step(self, date: datetime) -> int:
        return self.server.date_to_step(date)

    @property
    def step_size_in_seconds(self) -> float:
        return self.step_size_in_ms / 1000

    def start_server_async(self) -> threading.Thread:
        server_thread = threading.Thread(target=self.server.start)
        server_thread.daemon = True
        server_thread.start()
        return server_thread

    def start_server_and_wait_for_all_clients_connected_and_ready(self) -> threading.Thread:
        server_thread = threading.Thread(target=self.server.start_and_wait_for_all_clients_connected_and_ready)
        server_thread.daemon = True
        server_thread.start()
        return server_thread

    def start_client_1_async(self) -> None:
        self.client_1.start()

    def start_client_2_async(self) -> None:
        self.client_2.start()

    def verify_successful_run(self) -> None:
        client_1_measurement_repository = self.measurement_repository_client_1()

        if not isinstance(client_1_measurement_repository, MeasurementRepositoryInMemory):
            raise RuntimeError("You can only use in memory DBs")

        client_1_measurement_repository.assert_entry_count(self.steps)

        def assert_for_each_record(
            timestamp: datetime,
            values: Tuple[ProtocolInterfaceValue, ...],
        ) -> bool:
            current_step = self.date_to_step(timestamp)

            output_value: InterfaceValueType | None = None
            input_value: InterfaceValueType | None = None
            for value in values:
                if value.name == "Interface_Output_1":
                    output_value = value.value
                elif value.name == "Interface_Input_1":
                    input_value = value.value
            assert output_value is not None, f"Missing output interface value for step {current_step}"
            assert input_value is not None, f"Missing input interface value for step {current_step}"

            expected_output = self.client_1_output_value_at_step(int(current_step))
            expected_input = self.client_2_output_value_at_step(int(current_step))
            assert input_value == expected_input, f"failed at step {current_step} for input value: actual: {input_value} | expected {expected_input}"
            assert output_value == expected_output, (
                f"failed at step {current_step} for output value: actual: {output_value} | expected {expected_output}"
            )
            return values[0].value == expected_output

        client_1_measurement_repository.assert_for_each_record(assert_for_each_record)


# TODO_OSR: extract the logic and move the fixture
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
