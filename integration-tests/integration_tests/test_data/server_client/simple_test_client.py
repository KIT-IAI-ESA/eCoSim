from __future__ import annotations

from typing import Callable, override

from ecosim_common.client.client import Client
from ecosim_common.client.config.client_config import (
    ClientConfig,
    ClientInterfaceConfig,
    ServerConfig,
    SimulatorConfig,
)
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.renderer.simulation_renderer_service import (
    SimulationRendererService,
)
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.atomic import AtomicFloat, AtomicInteger
from integration_tests.test_data.test_client_data import TestClientData


def answer_start(_client: SimpleTestClient) -> ClientSimStepData:
    return ClientSimStepData(interface_values=[])


class SimpleTestClient(Client):
    @staticmethod
    def generate(
        communication_protocol: CommunicationProtocol,
        server_host: str,
        server_port: int,
        on_simulation_step_return: Callable[
            [SimpleTestClient, dict[InterfaceId, InterfaceValue], float],
            ClientSimStepData,
        ],
        model_name: str = "TestModel",
        simulator_name: str = "TestSimulator",
        interface_config: ClientInterfaceConfig = ClientInterfaceConfig(interfaces=[]),
    ) -> SimpleTestClient:
        return SimpleTestClient(
            client_config=TestClientConfig(
                server_host=server_host,
                server_port=server_port,
                simulator_name=simulator_name,
                model_name=model_name,
                interface_config=interface_config,
                communication_protocol=communication_protocol,
            ),
            on_simulation_step_return=on_simulation_step_return,
        )

    @staticmethod
    def of_test_data(
        server_host: str,
        server_port: int,
        on_simulation_step_return: Callable[
            [SimpleTestClient, dict[InterfaceId, InterfaceValue], float],
            ClientSimStepData,
        ],
        test_client_data: TestClientData,
        communication_protocol: CommunicationProtocol,
    ) -> SimpleTestClient:
        return SimpleTestClient(
            client_config=TestClientConfig(
                server_host=server_host,
                server_port=server_port,
                simulator_name=test_client_data.simulator_name,
                model_name=test_client_data.model_name,
                interface_config=test_client_data.to_client_interface_config(),
                communication_protocol=communication_protocol,
            ),
            on_simulation_step_return=on_simulation_step_return,
        )

    @staticmethod
    def sending_accumulated_step_sizes(
        communication_protocol: CommunicationProtocol,
        server_host: str,
        server_port: int,
        test_client_data: TestClientData,
        interface_name: str,
    ) -> SimpleTestClient:
        return SimpleTestClient.of_test_data(
            communication_protocol=communication_protocol,
            server_host=server_host,
            server_port=server_port,
            test_client_data=test_client_data,
            on_simulation_step_return=lambda client, _received_inputs, _step_size_in_seconds: ClientSimStepData(
                interface_values=[
                    test_client_data.interface_protocol_value_of(
                        interface_name=interface_name,
                        value=client.accumulated_step_sizes_in_seconds.value,
                    ),
                ],
            ),
        )

    def __init__(
        self,
        client_config: ClientConfig,
        on_simulation_step_return: Callable[
            [SimpleTestClient, dict[InterfaceId, InterfaceValue], float],
            ClientSimStepData,
        ],
        on_simulation_start_return: Callable[[SimpleTestClient], ClientSimStepData] = answer_start,
    ):
        super().__init__(client_config)
        self._on_simulation_start_calls = AtomicInteger.for_protocol(client_config.communication_protocol(), 0)
        self._on_simulation_step_calls = AtomicInteger.for_protocol(client_config.communication_protocol(), 0)
        self._on_simulation_stop_calls = AtomicInteger.for_protocol(client_config.communication_protocol(), 0)
        self.accumulated_step_sizes_in_seconds = AtomicFloat.for_protocol(client_config.communication_protocol(), 0.0)
        # the parameters: the instance of itself, the received_inputs and the step_size_in_seconds
        self._on_simulation_step_return: Callable[
            [SimpleTestClient, dict[InterfaceId, InterfaceValue], float],
            ClientSimStepData,
        ] = on_simulation_step_return
        self._on_simulation_start_return: Callable[[SimpleTestClient], ClientSimStepData] = on_simulation_start_return

    def reset_accumulated_step_sizes(self) -> None:
        self.accumulated_step_sizes_in_seconds.set(0.0)

    def on_simulation_start(self) -> ClientSimStepData:
        self._on_simulation_start_calls.increment()
        return self._on_simulation_start_return(self)

    def on_simulation_step(
        self,
        received_inputs: dict[InterfaceId, InterfaceValue],
        step_size_in_seconds: float,
    ) -> ClientSimStepData:
        self._on_simulation_step_calls.increment()
        self.accumulated_step_sizes_in_seconds.increment(step_size_in_seconds)
        return self._on_simulation_step_return(
            self,
            received_inputs,
            step_size_in_seconds,
        )

    @override
    def on_simulation_stop(self) -> None:
        self._on_simulation_stop_calls.increment()

    @override
    def image_renderer_service(self) -> SimulationRendererService:  # type: ignore # we don't need this in our test client
        pass


class TestClientConfig(ClientConfig):
    def __init__(
        self,
        server_host: str,
        server_port: int,
        simulator_name: str,
        model_name: str,
        interface_config: ClientInterfaceConfig,
        communication_protocol: CommunicationProtocol,
    ):
        self._simulator_name = simulator_name
        self._model_name = model_name
        self._server_config: ServerConfig = ServerConfig(
            server_address=ConnectionAddress(server_host, server_port),
            communication_protocol=communication_protocol,
        )
        self._interface_config = interface_config

    @override
    def server_config(self) -> ServerConfig:
        return self._server_config

    @override
    def interfaces_config(self) -> ClientInterfaceConfig:
        return self._interface_config

    @override
    def type(self) -> ClientType:
        return ClientType.FMU_3

    @override
    def simulator_config(self) -> SimulatorConfig:
        return SimulatorConfig(
            simulator_name=self._simulator_name,
            model_name=self._model_name,
            fmc_file="",
            type=ClientType.FMU_3,
        )

    @override
    def communication_protocol(self) -> CommunicationProtocol:
        return self._server_config.communication_protocol

    @override
    def as_config_file_content(self) -> str:
        return ""
