from ecosim_client_matlab.matlab_config import MatlabConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue, InterfaceValueType
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.client.config.client_config import ClientConfig
import io

try:
    import matlab.engine
except (ModuleNotFoundError, RuntimeError) as e:
    print(f"Matlab module not found. Either no valid matlab installation was found or a different Matlab Version is used: {e}")

"""
For the usage of the matlab simulator check the appropriate section in the README
"""


class MatlabSimulator(ShutdownListener):
    _logger = ESPLogger("MatlabSimulator")

    def __init__(
        self,
        execution_config: ExecutionConfig,
        client_config: ClientConfig,
        matlab_config: MatlabConfig,
    ):

        self._matlab_engine = matlab.engine.start_matlab()
        self._execution_config: ExecutionConfig = execution_config
        self._client_config: ClientConfig = client_config
        self._matlab_config: MatlabConfig = matlab_config
        self._start_time: float = 0.0
        self._is_initialized: bool = False
        self._is_cleared: bool = False
        self._current_simulation_time: float = 0.0
        ShutdownManager().register_listener(self)

    def initialize(
        self,
        start_time: float = 0.0,
    ) -> None:
        if self._is_initialized:
            MatlabSimulator._logger.warning("Already initialized ... aborting second initialization.")
            return
        MatlabSimulator._logger.info(f"Initializing with start_time {start_time}")
        self._start_time = start_time
        self._is_initialized = True
        self._current_simulation_time = start_time
        self._matlab_engine = matlab.engine.start_matlab()
        self._matlab_engine.addpath(self._matlab_config.folder_path)
        self._matlab_engine.setup(nargout=0)
        MatlabSimulator._logger.debug("Initializing... finished.")

    def set_input_float(
        self,
        name: str,
        value: float,
    ) -> None:
        MatlabSimulator._logger.debug(f"Setting float input {name} to {value}")
        self._matlab_engine.workspace[name] = value

    def get_output_float(
        self,
        name: str,
    ) -> float:
        value: float = self._matlab_engine.workspace[name]
        MatlabSimulator._logger.debug(f"Getting float output {name}: {value}")
        return value

    def server_used_output_values(self) -> ClientSimStepData:
        return ClientSimStepData.of_protocol_interface_values([
            ProtocolInterfaceValue(
                name=interface_name,
                # we always assume float (like in the Java client)
                value=self.get_output_float(interface_name),
            )
            for interface_name in self._execution_config.server_used_outputs()
        ])

    def do_step(
        self,
        input_values: dict[InterfaceId, InterfaceValueType],
        step_size_in_seconds: float,
    ) -> None:
        for interface_id, value in input_values.items():
            # TODO Alexander: implement to your needs (see the following example)
            '''
            if isinstance(value, float):
                self.set_input_float(interface_id, value)
            elif isinstance(value, list): # 'list' can contain lists
                pass
            elif value is None:
                pass
            '''
            self.set_input_float(interface_id, value)  # type: ignore  # TODO, s. comment above
        MatlabSimulator._logger.info(
            f"Executing next step (current_simulation_time={self._current_simulation_time} | step_size={step_size_in_seconds})...",
        )
        self._matlab_engine.workspace["client_time"] = self._current_simulation_time
        # Steps are starting at 0
        self._matlab_engine.workspace["step"] = (self._current_simulation_time / step_size_in_seconds) + 1
        self._matlab_engine.step(nargout=0, stdout=io.StringIO())
        self._current_simulation_time += step_size_in_seconds
        MatlabSimulator._logger.info(
            f"Executing next step finished (current_simulation_time={self._current_simulation_time}).",
        )

    def clear(self) -> None:
        if self._is_cleared:
            MatlabSimulator._logger.warning("Already cleared ... aborting second clearing.")
            return
        MatlabSimulator._logger.info("Clearing MatlabSimulatorV2...")
        MatlabSimulator._logger.debug("        ->> terminating instance...")
        self._matlab_engine.finishing(nargout=0, stdout=io.StringIO())
        self._matlab_engine.shutdown(nargout=0)
        MatlabSimulator._logger.debug("Clearing MatlabSimulatorV2...finished")
        self._is_cleared = True

    def on_app_shutdown(self) -> None:
        if not self._is_cleared:
            self.clear()
