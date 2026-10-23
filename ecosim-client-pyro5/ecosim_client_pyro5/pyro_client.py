from __future__ import annotations

from dataclasses import dataclass, field
from typing import override

import Pyro5.api
from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType
from ecosim_common.config.config_parser import ConfigParser

from ecosim_client_pyro5.pyro_config import PyroConfig


@dataclass(kw_only=True)
class PyroClient(SimulatorClient):
    _pyro_config: PyroConfig
    _simulation_object: Pyro5.api.Proxy
    _input_dict: dict[str, InterfaceValueType] = field(default_factory=dict)
    _output_dict: dict[str, float] = field(default_factory=dict)

    @staticmethod
    def of(
        config_parser: ConfigParser,
        config_override: ClientConfigOverride,
    ) -> PyroClient:
        client_config = SimpleClientConfig.of_config_parser(config_parser, config_override)
        pyro_config = PyroConfig.of(config_parser=config_parser)
        simulation_object = Pyro5.api.Proxy(f"PYRO:{pyro_config.object_name}@{pyro_config.host}:{pyro_config.port}")
        return PyroClient(
            _client_config=client_config,
            _pyro_config=pyro_config,
            _simulation_object=simulation_object,
        )

    def _on_initialize_model(
        self,
        start_time: float = 0.0,
    ) -> None:
        self._simulation_object._pyroClaimOwnership()
        self._output_dict = self._simulation_object.initialize()

    @override
    def _set_input_float(
        self,
        name: str,
        value: InterfaceValueType,
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._input_dict[name] = value

    @override
    def _set_input_float_matrix(
        self,
        name: str,
        value: InterfaceValueType,
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._input_dict[name] = value

    @override
    def _get_model_output(self, name: str) -> InterfaceValueType:
        return self._output_dict[name]

    @override
    def _before_handle_message(
        self,
        message: ESPChannelMessage,
    ) -> None:
        # noinspection protected-member
        self._simulation_object._pyroClaimOwnership()

    @override
    def _on_do_step(
        self,
        step_size_in_seconds: float,
    ) -> None:
        self._output_dict = self._simulation_object.do_step(self._input_dict)

    @override
    def _on_clear_simulator(self) -> None:
        if not self._is_initialized:
            self.logger.debug("Remote model was never initialized, nothing to clear.")
            return
        self._simulation_object._pyroClaimOwnership()
        self.logger.debug("        ->> terminating instance...")
        self._simulation_object.clear()
