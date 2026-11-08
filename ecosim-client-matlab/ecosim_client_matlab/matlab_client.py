from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Callable

from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_common.config.config_parser import ConfigParser
from typing_extensions import override

from ecosim_client_matlab.matlab_config import MatlabConfig
from ecosim_client_matlab.matlab_engine import MatlabEngine, MatlabScript, start_matlab


@dataclass(kw_only=True)
class MatlabClient(SimulatorClient):
    _matlab_config: MatlabConfig = field()
    _start_matlab: Callable[[], MatlabEngine] = field(default=start_matlab)
    # started with the model, not with the client - see '_on_initialize_model'
    _matlab_engine_or_none: MatlabEngine | None = field(default=None)

    @staticmethod
    def of(
        config_parser: ConfigParser,
        config_overrides: ClientConfigOverride,
        start_matlab: Callable[[], MatlabEngine] = start_matlab,
    ) -> MatlabClient:
        return MatlabClient(
            _execution_config=ExecutionConfig(),
            _matlab_config=MatlabConfig(config_parser),
            _client_config=SimpleClientConfig.of_config_parser(config_parser, config_overrides),
            _start_matlab=start_matlab,
        )

    @property
    def _matlab_engine(self) -> MatlabEngine:
        if self._matlab_engine_or_none is None:
            raise RuntimeError("Matlab engine is not started")
        return self._matlab_engine_or_none

    @override
    def _on_initialize_model(
        self,
        start_time: float = 0.0,
    ) -> None:
        self._matlab_engine_or_none = self._start_matlab()
        self._matlab_engine.addpath(str(self._matlab_config.folder_path))
        self._run_script(script=self._matlab_engine.setup)

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
        value: FloatMatrix,
    ) -> None:
        raise NotImplementedError("MatlabClient currently does not support float matrix.")

    @override
    def _get_model_output(
        self,
        name: str,
    ) -> InterfaceValue:
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
        self._run_script(script=self._matlab_engine.step)

    @override
    def _on_clear_simulator(self) -> None:
        engine = self._matlab_engine_or_none
        if engine is None:
            self.logger.debug("Matlab engine was never started, nothing to clear.")
            return
        self.logger.info("Clearing MatlabClient...")
        self._matlab_engine_or_none = None
        try:
            self._run_script(script=engine.finishing)
        finally:
            engine.quit()
        self.logger.debug("Clearing MatlabClient...finished")

    def _run_script(self, script: MatlabScript) -> None:
        output = io.StringIO()
        error_output = io.StringIO()
        try:
            script(nargout=0, stdout=output, stderr=error_output)
        finally:
            if output.getvalue().strip():
                self.logger.info("%s", output.getvalue().rstrip())
            if error_output.getvalue().strip():
                self.logger.warning("%s", error_output.getvalue().rstrip())
