from __future__ import annotations

from dataclasses import dataclass, field
from typing import override
from unittest.mock import MagicMock

from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue


@dataclass(kw_only=True)
class SpySimulatorClient(SimulatorClient):
    calls: list[str] = field(default_factory=list)

    @staticmethod
    def create(
        channel: ESPChannel | None = None,
        communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
    ) -> SpySimulatorClient:
        client_config = MagicMock(spec=ClientConfig)
        client_config.communication_protocol.return_value = communication_protocol
        return SpySimulatorClient(_client_config=client_config, _channel_or_none=channel)

    @override
    def _on_initialize_model(self, start_time: float) -> None:
        self.calls.append(f"initialize at {start_time}")

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
