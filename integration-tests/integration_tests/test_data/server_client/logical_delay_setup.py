"""A sender connected to a receiver through one logical delay, loaded from a real simulation file."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue, ProtocolInterfaceValue
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_input, create_logical_delay, create_output, create_simulator
from integration_tests.test_data.server_client.simple_test_client import SimpleTestClient
from integration_tests.test_data.server_client.simple_test_server import SimpleTestServer, SimpleTestServerParameters, generate_simple_test_server
from integration_tests.test_data.test_client_data import TestClientData

HOST = "localhost"
_SENDER_NAME = "sender"
_RECEIVER_NAME = "receiver"
_SENT_INTERFACE = "sent"


@dataclass
class RecordingReceiver:
    received_inputs: dict[InterfaceId, List[InterfaceValue]] = field(default_factory=dict)

    def on_simulation_step(
        self,
        _client: SimpleTestClient,
        received_inputs: dict[InterfaceId, InterfaceValue],
        _step_size_in_seconds: float,
    ) -> ClientSimStepData:
        for interface, value in received_inputs.items():
            self.received_inputs.setdefault(interface, []).append(value)
        return ClientSimStepData(interface_values=[])


def delayed_simulation_config(
    directory: Path,
    steps: int,
    delay: int,
    start_value: Any,
    receiver_name: str = _RECEIVER_NAME,
    receiver_model: str = _RECEIVER_NAME,
    delayed_input: str = "delayed",
    receiver_outputs: tuple[str, ...] = (),
) -> SimulationConfig:
    receiver_input = create_input(delayed_input, simulator="0", interface=_SENT_INTERFACE, delay_path=["1"])
    file = config_file(
        directory,
        create_simulator(_SENDER_NAME, create_output(_SENT_INTERFACE)),
        create_simulator(receiver_name, receiver_input, *[create_output(output) for output in receiver_outputs], model=receiver_model),
        logical_delays=[create_logical_delay(receiver_name, delayed_input, delay=delay, start_value=start_value)],
    )
    return SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=steps)


def server_on_free_port(
    communication_protocol: CommunicationProtocol,
    simulation_config: SimulationConfig,
) -> SimpleTestServer:
    return generate_simple_test_server(
        SimpleTestServerParameters.of_simulation_config(
            communication_protocol=communication_protocol,
            host=HOST,
            port=get_free_port(),
            simulation_config=simulation_config,
        ),
    )


def _client_with_one_interface(
    server: SimpleTestServer,
    name: str,
    interface: str,
    interface_type: InterfaceType,
    on_simulation_step_return: Callable[[SimpleTestClient, dict[InterfaceId, InterfaceValue], float], ClientSimStepData],
) -> SimpleTestClient:
    client_data = TestClientData(simulator_name=name, model_name=name, interfaces=[])
    client_data.add_interface(interface_name=interface, unit="", interface_type=interface_type)
    return SimpleTestClient.of_test_data(
        communication_protocol=server.communication_protocol(),
        server_host=HOST,
        server_port=server.port(),
        test_client_data=client_data,
        on_simulation_step_return=on_simulation_step_return,
    )


def receiver_client(server: SimpleTestServer, receiver: RecordingReceiver, interface: str) -> SimpleTestClient:
    return _client_with_one_interface(
        server=server,
        name=_RECEIVER_NAME,
        interface=interface,
        interface_type=InterfaceType.INPUT,
        on_simulation_step_return=receiver.on_simulation_step,
    )


def sender_client(
    server: SimpleTestServer,
    sent_value_after_seconds: Callable[[float], InterfaceValue],
) -> SimpleTestClient:
    return _client_with_one_interface(
        server=server,
        name=_SENDER_NAME,
        interface=_SENT_INTERFACE,
        interface_type=InterfaceType.OUTPUT,
        on_simulation_step_return=lambda client, _received_inputs, _step_size: ClientSimStepData(
            interface_values=[
                ProtocolInterfaceValue(name=_SENT_INTERFACE, value=sent_value_after_seconds(client.accumulated_step_sizes_in_seconds.value)),
            ],
        ),
    )
