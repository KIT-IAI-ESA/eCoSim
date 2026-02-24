from ecosim_client_pyro5.pyro_config import PyroConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue, InterfaceValueType
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.client.config.client_config import ClientConfig
import Pyro5.api

"""
For the usage of the Pyro simulator check the appropriate section in the README
"""


class PyroSimulator(ShutdownListener):
    _logger = ESPLogger("PyroSimulator")

    def __init__(
        self,
        execution_config: ExecutionConfig,
        client_config: ClientConfig,
        pyro_config: PyroConfig,
    ):
        self._execution_config: ExecutionConfig = execution_config
        self._client_config: ClientConfig = client_config
        self._start_time: float = 0.0
        self._is_initialized: bool = False
        self._is_cleared: bool = False
        self._current_simulation_time: float = 0.0
        self._simulation_object = Pyro5.api.Proxy(f"PYRO:{pyro_config.object_name}@{pyro_config.host}:{pyro_config.port}")
        self._input_dict: dict[str, InterfaceValueType] = {}
        self._output_dict: dict[str, float] = {}
        ShutdownManager().register_listener(self)

    def initialize(
        self,
        start_time: float = 0.0,
    ) -> None:
        if self._is_initialized:
            PyroSimulator._logger.warning("Already initialized ... aborting second initialization.")
            return
        PyroSimulator._logger.info(f"Initializing with start_time {start_time}")
        self._start_time = start_time
        self._is_initialized = True
        self._current_simulation_time = start_time
        self._simulation_object._pyroClaimOwnership()
        self._output_dict = self._simulation_object.initialize()
        PyroSimulator._logger.debug("Initializing... finished.")

    def set_input_float(
        self,
        name: str,
        value: InterfaceValueType,
    ) -> None:
        if not isinstance(value, float):
            raise TypeError(f"Expected a float but got {type(value)}.")
        PyroSimulator._logger.debug(f"Setting float input {name} to {value}")
        self._input_dict[name] = value

    def get_output_float(
        self,
        name: str,
    ) -> float:
        value = self._output_dict[name]
        PyroSimulator._logger.debug(f"Getting float output {name}: {value}")
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
        self._simulation_object._pyroClaimOwnership()
        for interface_id, value in input_values.items():
            self.set_input_float(interface_id, value)
        PyroSimulator._logger.info(
            f"Executing next step (current_simulation_time={self._current_simulation_time} | step_size={step_size_in_seconds})...",
        )
        self._output_dict = self._simulation_object.do_step(self._input_dict)
        self._current_simulation_time += step_size_in_seconds
        PyroSimulator._logger.info(
            f"Executing next step finished (current_simulation_time={self._current_simulation_time}).",
        )

    def clear(self) -> None:
        self._simulation_object._pyroClaimOwnership()
        if self._is_cleared:
            PyroSimulator._logger.warning("Already cleared ... aborting second clearing.")
            return
        PyroSimulator._logger.info("Clearing PyroSimulatorV2...")
        PyroSimulator._logger.debug("        ->> terminating instance...")
        self._simulation_object.clear()
        PyroSimulator._logger.debug("Clearing PyroSimulatorV2...finished")
        self._is_cleared = True

    def on_app_shutdown(self) -> None:
        if not self._is_cleared:
            self.clear()
