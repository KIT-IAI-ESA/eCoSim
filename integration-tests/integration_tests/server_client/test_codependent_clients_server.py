import threading
from datetime import datetime
from decimal import Decimal
from typing import Tuple

from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import ConnectedToData, ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from ecosim_test_common.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from ecosim_test_common.test_data.server_client.simple_test_client import SimpleTestClient
from ecosim_test_common.test_data.server_client.simple_test_server import SimpleTestServerParameters, generate_simple_test_server


def test_codependent_clients_server(communication_protocol: CommunicationProtocol) -> None:
    server_host = "localhost"
    server_port = 23921
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
                ClientSimulatorConfig(
                    simulator_name="TestSimulator_3",
                    model_name="TestModel_3",
                    client_id=ClientID(model_name="TestModel_3", simulator_name="TestSimulator_3"),
                    interfaces=[
                        ModelInterfaceServer(
                            SimulatorInterfaceId(
                                simulator_name="TestSimulator_3",
                                model_interface_id=ModelInterfaceId(
                                    model_name="TestModel_3",
                                    interface="TestInterface_3",
                                ),
                            ),
                            name="TestInterface_3",
                            unit="TestUnit",
                            description=None,
                            interface_type=InterfaceType.INPUT,
                            required=True,
                            connected_to=[
                                ConnectedToData(
                                    simulator_interface_id=SimulatorInterfaceId(
                                        simulator_name="TestSimulator_2",
                                        model_interface_id=ModelInterfaceId(
                                            interface="TestInterface_2_2",
                                            model_name="TestModel_2",
                                        ),
                                    ),
                                    delay_path=[],
                                ),
                            ],
                        ),
                        ModelInterfaceServer(
                            SimulatorInterfaceId(
                                simulator_name="TestSimulator_3",
                                model_interface_id=ModelInterfaceId(
                                    model_name="TestModel_3",
                                    interface="TestInterface_3_2",
                                ),
                            ),
                            name="TestInterface_3_2",
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
                    value=add_floats(_self.accumulated_step_sizes_in_seconds.value, 0.11),
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
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface_2_2",
                    value=add_floats(
                        _self.accumulated_step_sizes_in_seconds.value,
                        0.22,
                        get_decimal_part(list(received_inputs.values())[0]),
                    ),
                ),
            ],
        ),
    )
    client_3 = SimpleTestClient.generate(
        communication_protocol=communication_protocol,
        server_host=server_host,
        server_port=server_port,
        model_name="TestModel_3",
        simulator_name="TestSimulator_3",
        interface_config=ClientInterfaceConfig(
            interfaces=[
                ModelInterfaceClient(
                    model_interface_id=ModelInterfaceId(
                        model_name="TestModel_3",
                        interface="TestInterface_3",
                    ),
                    type=InterfaceType.INPUT,
                    name="TestInterface_3",
                    required=True,
                    description="TestDescription_3",
                    unit="TestUnit",
                ),
                ModelInterfaceClient(
                    model_interface_id=ModelInterfaceId(
                        model_name="TestModel_3",
                        interface="TestInterface_3_2",
                    ),
                    type=InterfaceType.OUTPUT,
                    name="TestInterface_3_2",
                    required=True,
                    description="TestDescription_3",
                    unit="TestUnit",
                ),
            ],
        ),
        on_simulation_step_return=lambda _self, received_inputs, current_step: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name="TestInterface_3_2",
                    value=add_floats(
                        _self.accumulated_step_sizes_in_seconds.value,
                        0.33,
                        get_decimal_part(
                            list(received_inputs.values())[0],
                        )
                        % 1,
                    ),
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
    server.print_measurement_statistics()

    client_1_measurement_repository = server.measurement_repository(client_id=client_1.client_id)
    if not isinstance(client_1_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_1_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        # adding the offset of the lambda from TestClient_1
        assert add_floats(((timestamp - simulation_start_date).total_seconds()), 0.11) == values[0].value
        return add_floats(((timestamp - simulation_start_date).total_seconds()), 0.11) == values[0].value

    (client_1_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_1_records))

    client_2_measurement_repository = server.measurement_repository(client_id=client_2.client_id)
    if not isinstance(client_2_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_2_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        # adding the offset of the lambda from TestClient_2 and adding the decimal part of the return of TestClient_1
        assert add_floats((timestamp - simulation_start_date).total_seconds(), 0.22, 0.11) == values[0].value
        return add_floats((timestamp - simulation_start_date).total_seconds(), 0.22, 0.11) == values[0].value

    (client_2_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_2_records))

    client_3_measurement_repository = server.measurement_repository(client_id=client_3.client_id)
    if not isinstance(client_3_measurement_repository, MeasurementRepositoryInMemory):
        raise RuntimeError("You can only use in memory DBs")

    def assert_client_3_records(timestamp: datetime, values: Tuple[ProtocolInterfaceValue, ...]) -> bool:
        # adding the offset of the lambda from TestClient_3 and adding the decimal part of the return of TestClient_2
        assert add_floats((timestamp - simulation_start_date).total_seconds(), 0.33, 0.33) == values[0].value
        return add_floats((timestamp - simulation_start_date).total_seconds(), 0.33, 0.33) == values[0].value

    (client_3_measurement_repository.assert_entry_count(steps).assert_for_each_record(assert_client_3_records))


def get_decimal_part(value: float) -> float:
    return float(Decimal(str(value)) % 1)


def add_floats(*floats: float) -> float:
    return float(sum([Decimal(str(f)) for f in floats]))
