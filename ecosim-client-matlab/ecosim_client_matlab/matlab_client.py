from __future__ import annotations

import io
from dataclasses import dataclass, field

from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType
from ecosim_common.config.config_parser import ConfigParser
from typing_extensions import override

from ecosim_client_matlab.matlab_config import MatlabConfig

try:
    import matlab.engine
except (ModuleNotFoundError, RuntimeError) as e:
    print(f"Matlab module not found. Either no valid matlab installation was found or a different Matlab Version is used: {e}")


@dataclass(kw_only=True)
class MatlabClient(SimulatorClient):
    _matlab_config: MatlabConfig = field()
    # started with the model, not with the client - see '_on_initialize_model'
    _matlab_engine_or_none: matlab.engine.MatlabEngine | None = field(default=None)

    @staticmethod
    def of(
        config_parser: ConfigParser,
        config_overrides: ClientConfigOverride,
    ) -> MatlabClient:
        return MatlabClient(
            _execution_config=ExecutionConfig(),
            _matlab_config=MatlabConfig(config_parser),
            _client_config=SimpleClientConfig.of_config_parser(config_parser, config_overrides),
        )

    @property
    def _matlab_engine(self) -> matlab.engine.MatlabEngine:
        if self._matlab_engine_or_none is None:
            raise RuntimeError("Matlab engine is not started")
        return self._matlab_engine_or_none

    @override
    def _on_initialize_model(
        self,
        start_time: float = 0.0,
    ) -> None:
        self._matlab_engine_or_none = matlab.engine.start_matlab()
        self._matlab_engine.addpath(self._matlab_config.folder_path)
        self._matlab_engine.setup(nargout=0)

    @override
    def _set_input_float(
        self,
        name: str,
        value: float | None,
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._matlab_engine.workspace[name] = value

    @override
    def _set_input_float_matrix(
        self,
        name: str,
        value: InterfaceValueType,
    ) -> None:
        raise NotImplementedError("MatlabClient currently does not support float matrix.")

    @override
    def _get_model_output(
        self,
        name: str,
    ) -> InterfaceValueType:
        value: float = self._matlab_engine.workspace[name]
        self.logger.debug("Getting float output %s: %s", name, value)
        return value

    @override
    def _on_do_step(
        self,
        step_size_in_seconds: float,
    ) -> None:
        self._matlab_engine.workspace["client_time"] = self._current_simulation_time
        # Steps are starting at 0
        self._matlab_engine.workspace["step"] = (self._current_simulation_time / step_size_in_seconds) + 1
        self._matlab_engine.step(nargout=0, stdout=io.StringIO())

    @override
    def _on_clear_simulator(self) -> None:
        if self._matlab_engine_or_none is None:
            self.logger.debug("Matlab engine was never started, nothing to clear.")
            return
        self.logger.info("Clearing MatlabClient...")
        self.logger.debug("        ->> terminating instance...")
        self._matlab_engine.finishing(nargout=0, stdout=io.StringIO())
        self._matlab_engine.shutdown(nargout=0)
        self.logger.debug("Clearing MatlabClient...finished")
