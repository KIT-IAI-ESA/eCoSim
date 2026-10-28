import socket
import time
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, ClassVar, Generator
from unittest.mock import MagicMock

import pytest
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue

from integration_tests.clients.base.base_simulation import BaseSimulation
from integration_tests.test_data.messages.step_batch_request import create_step_batch_message


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("localhost", 0))
        return int(probe.getsockname()[1])


def _eventually(condition: Callable[[], bool], timeout_in_seconds: float = 5) -> bool:
    deadline = time.monotonic() + timeout_in_seconds
    while not condition() and time.monotonic() < deadline:
        time.sleep(0.05)
    return condition()


class ClientBaseTest(ABC):
    """
    A concrete test inherits from this class (its name has to start with 'Test') and only says how its client
    is created and what its model computes. Each input of the client is fed by a driver client, which sends
    'input_value_generator(name, passed_seconds)'.
    """

    STEPS: ClassVar[int] = 10
    STEP_SIZE_IN_SECONDS: ClassVar[float] = 1.0

    @abstractmethod
    def create_client(self, config_override: ClientConfigOverride) -> SimulatorClient:
        pass

    @abstractmethod
    def assert_outputs(self, passed_seconds: float, outputs: dict[str, InterfaceValue]) -> None:
        pass

    @abstractmethod
    def input_value_generator(self, name: str, passed_seconds: float) -> InterfaceValue:
        pass

    @abstractmethod
    def assert_resources_released(self, client: SimulatorClient) -> None:
        """Asserts that the model behind the client holds nothing anymore (files, engines, remote state, ...)."""
        pass

    @pytest.fixture
    def simulation(self, communication_protocol: CommunicationProtocol) -> Generator[BaseSimulation, Any, None]:
        port = _free_port()
        override = ClientConfigOverride(server_host="localhost", server_port=port, communication_protocol=communication_protocol)
        simulation = BaseSimulation.of(self.create_client(override), "localhost", port, self.STEPS, self.input_value_generator)
        simulation.run()
        yield simulation

    def test_receives_the_inputs_of_the_driver(self, simulation: BaseSimulation) -> None:
        input_names = simulation.input_names()

        for passed_seconds, values in simulation.client_measurements().items():
            assert {name: values[name] for name in input_names} == {name: self.input_value_generator(name, passed_seconds) for name in input_names}

    def test_outputs_follow_the_model(self, simulation: BaseSimulation) -> None:
        output_names = simulation.output_names()

        for passed_seconds, values in sorted(simulation.client_measurements().items()):
            assert output_names <= values.keys(), f"missing outputs at {passed_seconds}s: {output_names - values.keys()}"
            self.assert_outputs(passed_seconds, {name: values[name] for name in output_names})

    def test_advances_the_simulation_time_once_per_step(self, simulation: BaseSimulation) -> None:
        assert simulation.client._current_simulation_time == self.STEPS * self.STEP_SIZE_IN_SECONDS  # noqa: SLF001

    def test_a_step_batch_advances_the_time_by_each_step_size(
        self,
        simulation: BaseSimulation,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        expected_simulation_time = simulation.current_simulation_time() + 3
        client = simulation.client
        monkeypatch.setattr(client, "_channel_or_none", MagicMock(spec=ESPChannel))

        client._handle_message(  # noqa: SLF001
            create_step_batch_message(
                input_interface_names=simulation.input_names(),
                start_date=simulation.current_time(),
                number_of_steps=3,
                step_size=1.0,
                input_value_generator=self.input_value_generator,
            ),
        )

        assert simulation.current_simulation_time() == expected_simulation_time
        client._channel.send.assert_called_once()  # type: ignore[attr-defined]  # noqa: SLF001

    def test_finishes_on_simulation_stop(
        self,
        simulation: BaseSimulation,
    ) -> None:
        assert _eventually(
            timeout_in_seconds=10,
            condition=lambda: simulation.client._is_finished,  # noqa: SLF001
        )

    def test_clears_the_simulator_on_shutdown(
        self,
        simulation: BaseSimulation,
    ) -> None:
        simulation.client.on_app_shutdown()

        assert simulation.client._is_cleared  # noqa: SLF001
        self.assert_resources_released(simulation.client)

    def test_shuts_down_without_ever_connecting(self) -> None:
        override = ClientConfigOverride(server_host="localhost", server_port=_free_port(), communication_protocol=CommunicationProtocol.TCP_SOCKET)
        client = self.create_client(override)
        executor = ThreadPoolExecutor(max_workers=1)

        executor.submit(client.on_app_shutdown).result(timeout=10)
        executor.shutdown(wait=False)

        assert client._is_cleared  # noqa: SLF001
        self.assert_resources_released(client)
