from __future__ import annotations

from dataclasses import dataclass
from typing import override

from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_common.config.config_parser import ConfigParser

from ecosim_client_python.python_config import PythonConfig
from ecosim_client_python.python_model import PythonModel


@dataclass(kw_only=True)
class PythonClient(SimulatorClient):
    _model: PythonModel

    @staticmethod
    def of(
        config_parser: ConfigParser,
        config_override: ClientConfigOverride,
    ) -> PythonClient:
        client_config = SimpleClientConfig.of_config_parser(config_parser=config_parser, config_override=config_override)
        python_config = PythonConfig.of(config_parser=config_parser)
        PythonClient.logger.info("Importing the model %s", python_config.model_reference)
        return PythonClient(_client_config=client_config, _model=PythonModel.of_config(config=python_config))

    @override
    def _on_initialize_model(
        self,
        start_time: float = 0.0,
    ) -> None:
        self._model.initialize()

    @override
    def _set_input_float(
        self,
        name: str,
        value: float | None,
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._model.set_input(name=name, value=value)

    @override
    def _set_input_float_matrix(
        self,
        name: str,
        value: FloatMatrix,
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._model.set_input(name=name, value=value)

    @override
    def _get_model_output(self, name: str) -> InterfaceValue:
        return self._model.output(name=name)

    @override
    def _on_do_step(
        self,
        step_size_in_seconds: float,
    ) -> None:
        self._model.do_step(current_simulation_time=self._current_simulation_time, step_size_in_seconds=step_size_in_seconds)

    @override
    def _on_clear_simulator(self) -> None:
        if not self._is_initialized:
            self.logger.debug("The model was never initialized, nothing to clear.")
            return
        self._model.clear()
