import threading
from datetime import datetime
from decimal import Decimal
from typing import Tuple

from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue, InterfaceValueType
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import ModelInterfaceServer, ConnectedToData
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from integration_tests.server_client.simple_test_client import SimpleTestClient
from integration_tests.server_client.simple_test_server import generate_simple_test_server
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory

logger = ESPLogger("TEST_MATRIX_TRANSFER")


def test_matrix_transfer() -> None:
    server_host = "localhost"
    server_port = 33771
    steps = 100
    step_size_in_ms = 2_000
    simulation_start_date: datetime = datetime(
        year=2025, month=1, day=1, hour=0, minute=0, second=0,
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
                    ), ModelInterfaceServer(
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
    )
    repositories = server.repositories

    client_1 = SimpleTestClient.generate(
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
        on_simulation_step_return=lambda _self,
                                         received_inputs,
                                         current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface_1",
                    value=generate_matrix(_self.accumulated_step_sizes_in_seconds.value),
                ),
            ],
                                         ),
    )
    client_2 = SimpleTestClient.generate(
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

    client_1_measurement_repository = repositories.measurement_repository(client_id=client_1._client_config.client_id())

    def client_1_asserts(
        timestamp: datetime,
        values: Tuple[ProtocolInterfaceValue, ...],
    ) -> bool:
        base_value = (timestamp - simulation_start_date).total_seconds() + (step_size_in_ms / 1000)
        expected = generate_matrix(base_value)
        actual = values[0].value
        logger.debug(f"(Client1) Expected: {expected}")
        logger.debug(f"(Client1) Actual:   {actual}")
        return actual == expected

    if not isinstance(client_1_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    (
        client_1_measurement_repository
        .assert_entry_count(steps)
        .assert_for_each_record(client_1_asserts)
    )

    client_2_measurement_repository = repositories.measurement_repository(client_id=client_2._client_config.client_id())
    if not isinstance(client_2_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def client_2_asserts(
        timestamp: datetime,
        values: Tuple[ProtocolInterfaceValue, ...],
    ) -> bool:
        base_value = (timestamp - simulation_start_date).total_seconds() + (step_size_in_ms / 1000)
        actual = values[0].value
        expected = square_each_element(generate_matrix(base_value))
        logger.debug(f"(Client2) Expected: {expected}")
        logger.debug(f"(Client2) Actual:   {actual}")
        return actual == expected

    (
        client_2_measurement_repository
        .assert_entry_count(steps)
        .assert_for_each_record(client_2_asserts)
    )


def get_decimal_part(value: float) -> float:
    return float(Decimal(str(value)) % 1)


def add_floats(*floats: float) -> float:
    return float(sum([Decimal(str(f)) for f in floats]))


def generate_matrix(input: float) -> InterfaceValueType:
    return [
        [input, add_floats(input, 1.0), add_floats(input, 2.0)],
        [add_floats(input, 3.0), add_floats(input, 4.0), add_floats(input, 5.0)],
        [add_floats(input, 6.0), add_floats(input, 7.0), add_floats(input, 8.0)],
    ]


def handle_client_2_sim_step(
    simple_test_client: SimpleTestClient,
    received_values: dict[InterfaceId, InterfaceValueType],
    step_size_in_seconds: float,
) -> ClientSimStepData:
    logger.debug(f"Received values: {received_values}")
    assert len(received_values.keys()) == 1
    received_value: InterfaceValueType = received_values['TestInterface_2']
    assert isinstance(received_value, list)
    return_value = square_each_element(received_value)
    logger.debug(f"Return value: {return_value}")
    return ClientSimStepData(
        interface_values=[
            ProtocolInterfaceValue(
                name="TestInterface_2_2",
                value=return_value,
            ),
        ],
    )


def square_each_element(matrix: InterfaceValueType) -> InterfaceValueType:
    return [
        [value * value for value in inner_list] for inner_list in matrix  # type: ignore
    ]
