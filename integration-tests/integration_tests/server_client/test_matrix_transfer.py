import threading
from datetime import datetime
from decimal import Decimal
from typing import Tuple, cast

from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue, ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import ConnectedToData, ModelInterfaceServer
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import (
    SimpleTestServer,
    SimpleTestServerParameters,
    generate_simple_test_server,
)

logger = ESPLogger("TEST_MATRIX_TRANSFER")


def test_matrix_transfer(communication_protocol: CommunicationProtocol) -> None:
    run_matrix_transfer(communication_protocol)


def run_matrix_transfer(communication_protocol: CommunicationProtocol) -> SimpleTestServer:
    server_host = "localhost"
    server_port = get_free_port()
    steps = 100
    step_size_in_ms = 2_000
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
        SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host=server_host,
            port=server_port,
            steps=steps,
            step_size_in_ms=step_size_in_ms,
            simulation_start_date=simulation_start_date,
            clients=[
                ClientSimulatorConfig(
                    simulator_name="TestSimulator_1",
                    model_name="TestModel_1",
                    client_id=ClientID(model_name="TestModel_1", simulator_name="TestSimulator_1"),
                    interfaces=[
                        ModelInterfaceServer(
                            SimulatorInterfaceId(
                                simulator_name="TestSimulator_1",
                                model_interface_id=ModelInterfaceId(
                                    model_name="TestModel_1",
                                    interface="TestInterface_1",
                                ),
                            ),
                            name="TestInterface_1",
                            unit="TestUnit",
                            description=None,
                            interface_type=InterfaceType.OUTPUT,
                            required=True,
                            connected_to=[],
                        ),
                    ],
                ),
                ClientSimulatorConfig(
                    simulator_name="TestSimulator_2",
                    model_name="TestModel_2",
                    client_id=ClientID(model_name="TestModel_2", simulator_name="TestSimulator_2"),
                    interfaces=[
                        ModelInterfaceServer(
                            SimulatorInterfaceId(
                                simulator_name="TestSimulator_2",
                                model_interface_id=ModelInterfaceId(
                                    model_name="TestModel_2",
                                    interface="TestInterface_2",
                                ),
                            ),
                            name="TestInterface_2",
                            unit="TestUnit",
                            description=None,
                            interface_type=InterfaceType.INPUT,
                            required=True,
                            connected_to=[
                                ConnectedToData(
                                    simulator_interface_id=SimulatorInterfaceId(
                                        simulator_name="TestSimulator_1",
                                        model_interface_id=ModelInterfaceId(
                                            interface="TestInterface_1",
                                            model_name="TestModel_1",
                                        ),
                                    ),
                                    delay_path=[],
                                ),
                            ],
                        ),
                        ModelInterfaceServer(
                            SimulatorInterfaceId(
                                simulator_name="TestSimulator_2",
                                model_interface_id=ModelInterfaceId(
                                    model_name="TestModel_2",
                                    interface="TestInterface_2_2",
                                ),
                            ),
                            name="TestInterface_2_2",
                            unit="TestUnit",
                            description=None,
                            interface_type=InterfaceType.OUTPUT,
                            required=True,
                            connected_to=[],
                        ),
                    ],
                ),
            ],
        ),
    )

    client_1 = SimpleTestClient.generate(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        model_name="TestModel_1",
        simulator_name="TestSimulator_1",
        interface_config=ClientInterfaceConfig(
            interfaces=[
                ModelInterfaceClient(
                    model_interface_id=ModelInterfaceId(
                        model_name="TestModel_1",
                        interface="TestInterface_1",
                    ),
                    type=InterfaceType.OUTPUT,
                    name="TestInterface_1",
                    required=True,
                    description="TestDescription_1",
                    unit="TestUnit",
                ),
            ],
        ),
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface_1",
                    value=generate_matrix(_self.accumulated_step_sizes_in_seconds.value),
                ),
            ],
        ),
    )
    client_2 = SimpleTestClient.generate(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        model_name="TestModel_2",
        simulator_name="TestSimulator_2",
        interface_config=ClientInterfaceConfig(
            interfaces=[
                ModelInterfaceClient(
                    model_interface_id=ModelInterfaceId(
                        model_name="TestModel_2",
                        interface="TestInterface_2",
                    ),
                    type=InterfaceType.INPUT,
                    name="TestInterface_2",
                    required=True,
                    description="TestDescription_2",
                    unit="TestUnit",
                ),
                ModelInterfaceClient(
                    model_interface_id=ModelInterfaceId(
                        model_name="TestModel_2",
                        interface="TestInterface_2_2",
                    ),
                    type=InterfaceType.OUTPUT,
                    name="TestInterface_2_2",
                    required=True,
                    description="TestDescription_2",
                    unit="TestUnit",
                ),
            ],
        ),
        on_simulation_step_return=handle_client_2_sim_step,
    )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    client_1.start()
    client_2.start()

    server_thread.join()
    server.print_measurement_statistics()

    client_1_measurement_repository = server.measurement_repository(client_id=client_1.client_id)

    def client_1_asserts(
        timestamp: datetime,
        values: Tuple[ProtocolInterfaceValue, ...],
    ) -> bool:
        base_value = (timestamp - simulation_start_date).total_seconds()
        expected = generate_matrix(base_value)
        actual = values[0].value
        assert actual == expected, f"Expected: {expected}, Actual: {actual}"
        return actual == expected

    if not isinstance(client_1_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    (client_1_measurement_repository.assert_entry_count(steps).assert_for_each_record(client_1_asserts))

    client_2_measurement_repository = server.measurement_repository(client_id=client_2.client_id)
    if not isinstance(client_2_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def client_2_asserts(
        timestamp: datetime,
        values: Tuple[ProtocolInterfaceValue, ...],
    ) -> bool:
        base_value = (timestamp - simulation_start_date).total_seconds()
        actual = values[0].value
        expected = square_each_element(generate_matrix(base_value))
        assert actual == expected, f"Expected: {expected}, Actual: {actual}"
        return actual == expected

    (client_2_measurement_repository.assert_entry_count(steps).assert_for_each_record(client_2_asserts))

    return server


def get_decimal_part(value: float) -> float:
    return float(Decimal(str(value)) % 1)


def add_floats(*floats: float) -> float:
    return float(sum([Decimal(str(f)) for f in floats]))


def generate_matrix(input: float) -> list[FloatMatrix]:
    return [
        [input, add_floats(input, 1.0), add_floats(input, 2.0)],
        [add_floats(input, 3.0), add_floats(input, 4.0), add_floats(input, 5.0)],
        [add_floats(input, 6.0), add_floats(input, 7.0), add_floats(input, 8.0)],
    ]


def handle_client_2_sim_step(
    simple_test_client: SimpleTestClient,
    received_values: dict[InterfaceId, InterfaceValue],
    step_size_in_seconds: float,
) -> ClientSimStepData:
    logger.debug("Received values: %s", received_values)
    assert len(received_values.keys()) == 1
    received_value: InterfaceValue = received_values["TestInterface_2"]
    assert isinstance(received_value, list)
    return_value = square_each_element(received_value)
    logger.debug("Return value: %s", return_value)
    return ClientSimStepData(
        interface_values=[
            ProtocolInterfaceValue(
                name="TestInterface_2_2",
                value=return_value,
            ),
        ],
    )


def square_each_element(matrix: FloatMatrix) -> list[FloatMatrix]:
    # the test sends 3x3 matrices of floats only
    rows = cast(list[list[float]], matrix)
    return [[value * value for value in row] for row in rows]
