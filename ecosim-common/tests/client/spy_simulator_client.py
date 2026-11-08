from __future__ import annotations

from dataclasses import dataclass, field
from typing import override

from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config


@dataclass(kw_only=True)
class SpySimulatorClient(SimulatorClient):
    calls: list[str] = field(default_factory=list)
    initialize_fails: bool = field(default=False)
    stop_fails: bool = field(default=False)

    @staticmethod
    def create(
        channel: ESPChannel | None = None,
        communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
        server_address: ConnectionAddress | None = None,
        initialize_fails: bool = False,
        stop_fails: bool = False,
    ) -> SpySimulatorClient:
        return SpySimulatorClient(
            _client_config=generate_mocked_client_config(communication_protocol=communication_protocol, server_address=server_address),
            _channel_or_none=channel,
            initialize_fails=initialize_fails,
            stop_fails=stop_fails,
        )

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

    @override
    def _get_model_output(self, name: str) -> InterfaceValue:
        return 0.0

    @override
    def _on_clear_simulator(self) -> None:
        self.calls.append("clear")
