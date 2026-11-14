from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import override

from ecosim_common.client.config.client_config import SimulatorConfig
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_test_common.bounded_wait import finishes_in_time
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config
from ecosim_test_common.test_data.single_connection_server import SingleConnectionServer
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS


@dataclass(kw_only=True)
class SpySimulatorClient(SimulatorClient):
    calls: list[str] = field(default_factory=list)
    initialize_fails: bool = field(default=False)
    stop_fails: bool = field(default=False)
    failing_step: int | None = field(default=None)
    step_blocks: bool = field(default=False)
    step_block_started: threading.Event = field(default_factory=threading.Event)
    step_block_end: threading.Event = field(default_factory=threading.Event)
    model_problem: str | None = field(default=None)

    @staticmethod
    def create(
        channel: ESPChannel | None = None,
        communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
    ) -> SpySimulatorClient:
        return SpySimulatorClient(
            _client_config=generate_mocked_client_config(communication_protocol),
            _channel_or_none=channel,
        )

    @staticmethod
    def of_ended_run(
        message_types: list[MessageType],
        payloads: dict[MessageType, MessageData] | None = None,
        initialize_fails: bool = False,
        stop_fails: bool = False,
        model_problem: str | None = None,
        failing_step: int | None = None,
        client_id: ClientID = ClientID(model_name="house", simulator_name="house"),
        simulator_config: SimulatorConfig | None = None,
    ) -> SpySimulatorClient:
        """The client after a server sent it these messages and closed the connection."""
        server = SingleConnectionServer.listen()
        client = SpySimulatorClient(
            _client_config=generate_mocked_client_config(server_address=server.address(), client_id=client_id, simulator_config=simulator_config),
            initialize_fails=initialize_fails,
            stop_fails=stop_fails,
            model_problem=model_problem,
            failing_step=failing_step,
        )
        client.start()
        server.serve_and_close(message_types=message_types, payloads=payloads)
        assert finishes_in_time(blocking_call=client.wait_until_finished), "the client kept waiting after the server closed the connection"
        return client

    @override
    def _reason_the_model_cannot_run(self, server_interface_settings: ServerInterfaceSettings) -> str | None:
        return self.model_problem

    @override
    def _on_initialize_model(self, start_time: float) -> None:
        self.calls.append(f"initialize at {start_time}")
        if self.initialize_fails:
            raise RuntimeError("initialize failed")

    @override
    def on_simulation_stop(self) -> None:
        if self.stop_fails:
            raise RuntimeError("stop failed")

    @override
    def _set_input_float(self, name: str, value: float | None) -> None:
        self.calls.append(f"float {name}={value}")

    @override
    def _set_input_float_matrix(self, name: str, value: FloatMatrix) -> None:
        self.calls.append(f"matrix {name}={value}")

    @override
    def _on_do_step(self, step_size_in_seconds: float) -> None:
        self.calls.append(f"step of {step_size_in_seconds} at {self._current_simulation_time}")
        if self.failing_step == self.completed_steps:
            raise RuntimeError("step failed")
        if self.step_blocks:
            self.step_block_started.set()
            self.step_block_end.wait(timeout=WAIT_TIMEOUT_IN_SECONDS)

    @override
    def _get_model_output(self, name: str) -> InterfaceValue:
        return 0.0

    @override
    def _on_clear_simulator(self) -> None:
        self.calls.append("clear")
