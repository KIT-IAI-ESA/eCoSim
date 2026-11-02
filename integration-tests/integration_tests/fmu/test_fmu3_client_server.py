import threading
from datetime import datetime
from typing import Tuple

from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_common.client.config.client_config import ClientConfigOverride, ClientInterfaceConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import ConnectedToData, ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from integration_tests.fmu.fmu3_state_space_model import state_space_outputs
from integration_tests.tech.db.measurement_repository_in_memory import MeasurementRepositoryInMemory
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import config_parser_for_resource, fmu3_model_path
from integration_tests.test_data.server_client.server_thread import assert_server_finishes_in_time
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServerParameters, generate_simple_test_server


@skip_unless_fmpy_loads(fmu3_model_path())
def test_fmu3_client_server(communication_protocol: CommunicationProtocol) -> None:
    mock_client_interface = SimulatorInterfaceId(
        simulator_name="Mock_1",
        model_interface_id=ModelInterfaceId(
            model_name="Mock_1",
            interface="Interface_1",
        ),
    )
    server_host = "localhost"
    server_port = get_free_port()
    steps = 100
    start_date = datetime(2020, 1, 1)
    server = generate_simple_test_server(
        SimpleTestServerParameters(
            communication_protocol=communication_protocol,
            host=server_host,
            port=server_port,
            steps=steps,
            simulation_start_date=start_date,
            clients=[
                ClientSimulatorConfig(
                    simulator_name=mock_client_interface.simulator_name,
                    model_name=mock_client_interface.model_interface_id.model_name,
                    client_id=ClientID(
                        model_name=mock_client_interface.model_interface_id.model_name,
                        simulator_name=mock_client_interface.simulator_name,
                    ),
                    interfaces=[
                        ModelInterfaceServer(
                            simulator_interface_id=mock_client_interface,
                            name=mock_client_interface.model_interface_id.interface,
                            unit="float64_matrix",
                            description="",
                            interface_type=InterfaceType.OUTPUT,
                            required=True,
                            connected_to=[],
                        ),
                    ],
                ),
                ClientSimulatorConfig(
                    simulator_name="fmu3",
                    model_name="state_space",
                    client_id=ClientID(model_name="state_space", simulator_name="fmu3"),
                    interfaces=[
                        ModelInterfaceServer(
                            SimulatorInterfaceId(
                                simulator_name="fmu3",
                                model_interface_id=ModelInterfaceId(
                                    model_name="state_space",
                                    interface="u",
                                ),
                            ),
                            name="u",
                            unit="float64_matrix",
                            description="",
                            interface_type=InterfaceType.INPUT,
                            required=True,
                            connected_to=[
                                ConnectedToData(
                                    simulator_interface_id=mock_client_interface,
                                    delay_path=[],
                                ),
                            ],
                        ),
                        ModelInterfaceServer(
                            SimulatorInterfaceId(
                                simulator_name="fmu3",
                                model_interface_id=ModelInterfaceId(
                                    model_name="state_space",
                                    interface="y",
                                ),
                            ),
                            name="y",
                            description="",
                            unit="",
                            interface_type=InterfaceType.OUTPUT,
                            required=True,
                            connected_to=[
                                ConnectedToData(
                                    simulator_interface_id=mock_client_interface,
                                    delay_path=[],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    )

    mock_client = SimpleTestClient.generate(
        communication_protocol=communication_protocol,
        simulator_name=mock_client_interface.simulator_name,
        model_name=mock_client_interface.model_interface_id.model_name,
        server_host=server_host,
        server_port=server_port,
        interface_config=ClientInterfaceConfig(
            interfaces=[
                ModelInterfaceClient(
                    name=mock_client_interface.model_interface_id.interface,
                    type=InterfaceType.OUTPUT,
                    unit=None,
                    description="",
                    required=False,
                    model_interface_id=mock_client_interface.model_interface_id,
                ),
            ],
        ),
        on_simulation_step_return=lambda _self, received_inputs, steps: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(
                    name=mock_client_interface.model_interface_id.interface,
                    value=[
                        1 * _self.accumulated_step_sizes_in_seconds.value,
                        1_000 * _self.accumulated_step_sizes_in_seconds.value,
                        100_000 * _self.accumulated_step_sizes_in_seconds.value,
                    ],
                ),
            ],
        ),
    )

    fmu3_client = FMU3Client.of(
        config_parser=config_parser_for_resource("integration/models/fmu3/configs/state_space.ini"),
        config_override=ClientConfigOverride(
            server_host=server_host,
            server_port=server_port,
            communication_protocol=communication_protocol,
        ),
    )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()

    fmu3_client.start()
    mock_client.start()

    assert_server_finishes_in_time(server_thread)

    fmu3_measurement_repo: MeasurementRepositoryInMemory = server.measurement_repository(fmu3_client.client_id)  # type: ignore
    fmu3_measurement_repo.assert_entry_count(steps)

    def assert_for_each_record(
        date: datetime,
        values: Tuple[ProtocolInterfaceValue, ...],
    ) -> bool:
        passed_seconds = (date - start_date).total_seconds()
        u = [v for v in values if v.name == "u"][0]
        y = [v for v in values if v.name == "y"][0]

        assert u.value == [1 * passed_seconds, 1_000 * passed_seconds, 100_000 * passed_seconds]
        expected_y = state_space_outputs(int(passed_seconds), (1, 1_000, 100_000))
        assert y.value == expected_y

        return u.value == [1 * passed_seconds, 1_000 * passed_seconds, 100_000 * passed_seconds] and y.value == expected_y

    fmu3_measurement_repo.assert_for_each_record(assertion=assert_for_each_record)
