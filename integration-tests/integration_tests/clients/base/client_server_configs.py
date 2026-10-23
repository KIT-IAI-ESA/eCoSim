from typing import Callable

from ecosim_common.client.config.client_config import ClientInterfaceConfig
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType, ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.config.model_interface_server import ConnectedToData, ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_common.simulation.simulator_interface_id import SimulatorInterfaceId
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient

DRIVER_NAME = "ProtocolDriver"
"""Simulator and model name of the driver client, which provides one output per input of the client under test."""

InputValueGenerator = Callable[[str, float], InterfaceValueType]
"""The value the driver sends to an input of the client under test: (input name, passed seconds) -> value."""

ClientMeasurementRecords = dict[float, dict[str, InterfaceValueType]]
"""The recorded values of the client under test: passed seconds -> interface name -> value."""


def create_driver_client_for(
    protocol: CommunicationProtocol,
    host: str,
    port: int,
    client_interfaces: ClientInterfaceConfig,
    input_value_generator: InputValueGenerator,
) -> SimpleTestClient:
    names = client_interfaces.input_interface_names()
    return SimpleTestClient.generate(
        communication_protocol=protocol,
        server_host=host,
        server_port=port,
        model_name=DRIVER_NAME,
        simulator_name=DRIVER_NAME,
        interface_config=driver_interface_config(client_interfaces),
        on_simulation_step_return=lambda driver, _inputs, _step_size: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(name=name, value=input_value_generator(name, driver.accumulated_step_sizes_in_seconds.value)) for name in names
            ],
        ),
    )


def driver_interface_id(name: str) -> SimulatorInterfaceId:
    return SimulatorInterfaceId(
        simulator_name=DRIVER_NAME,
        model_interface_id=ModelInterfaceId(model_name=DRIVER_NAME, interface=name),
    )


def driver_interface_config(client_interfaces: ClientInterfaceConfig) -> ClientInterfaceConfig:
    return ClientInterfaceConfig(
        interfaces=[
            ModelInterfaceClient(
                model_interface_id=driver_interface_id(name).model_interface_id,
                name=name,
                unit=None,
                description="",
                type=InterfaceType.OUTPUT,
                required=False,
            )
            for name in _input_names(client_interfaces)
        ],
    )


def _input_names(interface_config: ClientInterfaceConfig) -> list[str]:
    return interface_config.input_interface_names()


def driver_simulator_config(client_interfaces: ClientInterfaceConfig) -> ClientSimulatorConfig:
    return ClientSimulatorConfig(
        simulator_name=DRIVER_NAME,
        model_name=DRIVER_NAME,
        client_id=ClientID(model_name=DRIVER_NAME, simulator_name=DRIVER_NAME),
        interfaces=[_server_interface(driver_interface_id(name), InterfaceType.OUTPUT, []) for name in _input_names(client_interfaces)],
    )


def client_simulator_config(
    client_id: ClientID,
    client_interfaces: ClientInterfaceConfig,
) -> ClientSimulatorConfig:
    return ClientSimulatorConfig(
        simulator_name=client_id.simulator_name,
        model_name=client_id.model_name,
        client_id=client_id,
        interfaces=[_client_server_interface(client_id, interface) for interface in client_interfaces.interfaces],
    )


def _client_server_interface(
    client_id: ClientID,
    interface: ModelInterfaceClient,
) -> ModelInterfaceServer:
    connected_to = []
    if interface.type == InterfaceType.INPUT:
        connected_to = [ConnectedToData(simulator_interface_id=driver_interface_id(interface.name), delay_path=[])]
    simulator_interface_id = SimulatorInterfaceId(
        simulator_name=client_id.simulator_name,
        model_interface_id=interface.model_interface_id,
    )
    return _server_interface(simulator_interface_id, interface.type, connected_to, interface.required)


def _server_interface(
    simulator_interface_id: SimulatorInterfaceId,
    interface_type: InterfaceType,
    connected_to: list[ConnectedToData],
    required: bool = False,
) -> ModelInterfaceServer:
    return ModelInterfaceServer(
        simulator_interface_id=simulator_interface_id,
        name=simulator_interface_id.model_interface_id.interface,
        unit="",
        description="",
        interface_type=interface_type,
        required=required,
        connected_to=connected_to,
    )
