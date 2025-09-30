from __future__ import annotations

from typing import Callable, override

from ecosim_common.client.client import Client
from ecosim_common.client.config.client_config import ClientConfig, SimulatorConfig, ClientInterfaceConfig, ServerConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.client.renderer.simulation_renderer_service import SimulationRendererService
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.atomic.atomic_float import AtomicFloat
from ecosim_common.tech.atomic.atomic_integer import AtomicInteger


class SimpleTestClient(Client):

    @staticmethod
    def generate(
            server_host: str,
            server_port: int,
            on_simulation_step_return: Callable[[SimpleTestClient, dict[InterfaceId, InterfaceValueType], float], ClientSimStepData],
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
            ),
            on_simulation_step_return=on_simulation_step_return,
        )

    def __init__(self,
                 client_config: ClientConfig,
                 on_simulation_step_return: Callable[
                     [SimpleTestClient, dict[InterfaceId, InterfaceValueType], float], ClientSimStepData],
                 ):
        super().__init__(client_config)
        self._on_simulation_start_calls = AtomicInteger(0)
        self._on_simulation_step_calls = AtomicInteger(0)
        self._on_simulation_stop_calls = AtomicInteger(0)
        self.accumulated_step_sizes_in_seconds = AtomicFloat(0.0)
        # the parameters: the instance of itself, the received_inputs and the step_size_in_seconds
        self._on_simulation_step_return: Callable[
            [SimpleTestClient, dict[InterfaceId, InterfaceValueType], float], ClientSimStepData] = on_simulation_step_return

    def on_simulation_start(self) -> ClientSimStepData:
        self._on_simulation_start_calls.inc()
        return ClientSimStepData(
            interface_values=[]
        )

    def on_simulation_step(self,
                           received_inputs: dict[InterfaceId, InterfaceValueType],
                           step_size_in_seconds: float,
                           ) -> ClientSimStepData:
        self._on_simulation_step_calls.inc()
        self.accumulated_step_sizes_in_seconds.inc(step_size_in_seconds)
        return self._on_simulation_step_return(self, received_inputs, step_size_in_seconds)

    @override
    def on_simulation_stop(self) -> None:
        self._on_simulation_stop_calls.inc()

    @override
    def image_renderer_service(self) -> SimulationRendererService:  # type: ignore # we don't need this in our test client
        pass


class TestClientConfig(ClientConfig):

    def __init__(self,
                 server_host: str,
                 server_port: int,
                 simulator_name: str,
                 model_name: str,
                 interface_config: ClientInterfaceConfig,
                 ):
        self._simulator_name = simulator_name
        self._model_name = model_name
        self._server_config: ServerConfig = ServerConfig(
            server_address=ConnectionAddress(server_host, server_port),
        )
        self._interface_config = interface_config

    def server_config(self) -> ServerConfig:
        return self._server_config

    def interfaces_config(self) -> ClientInterfaceConfig:
        return self._interface_config

    def type(self) -> ClientType:
        return ClientType.FMU_3

    def simulator_config(self) -> SimulatorConfig:
        return SimulatorConfig(
            simulator_name=self._simulator_name,
            model_name=self._model_name,
            fmc_file="",
            type=ClientType.FMU_3,
        )
