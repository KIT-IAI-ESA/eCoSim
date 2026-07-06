import shutil
from typing import override

import fmpy.fmi2
from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType, ProtocolInterfaceValue
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig


class FMU2Simulator(ShutdownListener):
    _logger = ESPLogger("FMUSimulatorV2")

    @classmethod
    def of(
        cls,
        simulator_name: str,
        fmu_config: FMUBaseConfig,
        execution_config: ExecutionConfig,
    ) -> "FMU2Simulator":
        simulator_config = FMU2SimulatorConfig.of(
            simulator_name=simulator_name,
            fmu_config=fmu_config,
        )
        return FMU2Simulator(
            simulation_config=simulator_config,
            execution_config=execution_config,
            fmu_instance=simulator_config.create_fmu2_instance(),
        )

    def __init__(
        self,
        simulation_config: FMU2SimulatorConfig,
        execution_config: ExecutionConfig,
        fmu_instance: fmpy.fmi2.FMU2Slave,
    ) -> None:
        GlobalLogger.print_values(
            header="FMU CONFIG",
            value_pairs={
                "FMU instance": fmu_instance.instanceName,
                "FMI version": simulation_config.fmi_version(),
            },
        )
        self._simulation_config: FMU2SimulatorConfig = simulation_config
        self._execution_config: ExecutionConfig = execution_config
        self._fmu_instance: fmpy.fmi2.FMU2Slave = fmu_instance
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
            FMU2Simulator._logger.warning("Already initialized ... aborting second initialization.")
            return
        FMU2Simulator._logger.info(f"Initializing with start_time {start_time}")
        self._start_time = start_time
        self._fmu_instance.instantiate()
        self._fmu_instance.setupExperiment(startTime=start_time)
        self._fmu_instance.enterInitializationMode()
        self._fmu_instance.exitInitializationMode()
        self._is_initialized = True
        self._current_simulation_time = start_time
        FMU2Simulator._logger.debug("Initializing... finished.")

    def set_input_float(
        self,
        name: str,
        value: InterfaceValueType,
    ) -> None:
        if not isinstance(value, float):
            raise TypeError(f"Expected a float but got {type(value)}.")
        FMU2Simulator._logger.debug(f"Setting float input {name} to {value}")
        self._fmu_instance.setReal([self._simulation_config.input_value_references(name)], [value])

    def set_input_string(
        self,
        name: str,
        value: str,
    ) -> None:
        FMU2Simulator._logger.debug(f"Setting string input {name} to {value}")
        self._fmu_instance.setString([self._simulation_config.input_value_references(name)], [value])

    def set_input_boolean(
        self,
        name: str,
        value: bool,
    ) -> None:
        FMU2Simulator._logger.debug(f"Setting bool input {name} to {value}")
        self._fmu_instance.setBoolean([self._simulation_config.input_value_references(name)], [value])

    def get_output_float(
        self,
        name: str,
    ) -> float:
        value: float = self._fmu_instance.getReal([self._simulation_config.output_value_references(name)])[0]
        FMU2Simulator._logger.debug(f"Getting float output {name}: {value}")
        return value

    def get_output_string(
        self,
        name: str,
    ) -> str:
        value: str = self._fmu_instance.getString([self._simulation_config.output_value_references(name)])
        FMU2Simulator._logger.debug(f"Getting string output {name}: {value}")
        return value

    def server_used_output_values(self) -> ClientSimStepData:
        return ClientSimStepData.of_protocol_interface_values(
            [
                ProtocolInterfaceValue(
                    name=interface_name,
                    # we always assume float (like in the Java client)
                    value=self.get_output_float(interface_name),
                )
                for interface_name in self._execution_config.server_used_outputs()
            ],
        )

    def get_output_boolean(
        self,
        name: str,
    ) -> bool:
        value: bool = self._fmu_instance.getBoolean([self._simulation_config.output_value_references(name)])
        FMU2Simulator._logger.debug(f"Getting bool output {name}: {value}")
        return value

    def do_step(
        self,
        input_values: dict[InterfaceId, InterfaceValueType],
        step_size_in_seconds: float,
    ) -> None:
        for interface_id, value in input_values.items():
            self.set_input_float(interface_id, value)
        FMU2Simulator._logger.info(
            f"Executing next step (current_simulation_time={self._current_simulation_time} | step_size={step_size_in_seconds})...",
        )
        self._fmu_instance.doStep(
            currentCommunicationPoint=self._current_simulation_time,
            communicationStepSize=step_size_in_seconds,
        )
        self._current_simulation_time += step_size_in_seconds
        FMU2Simulator._logger.info(
            f"Executing next step finished (current_simulation_time={self._current_simulation_time}).",
        )

    def clear(self) -> None:
        if self._is_cleared:
            FMU2Simulator._logger.warning("Already cleared ... aborting second clearing.")
            return
        FMU2Simulator._logger.info("Clearing FMUSimulatorV2...")
        FMU2Simulator._logger.debug("        ->> terminating instance...")
        self._fmu_instance.terminate()
        FMU2Simulator._logger.debug("        ->> freeing instance...")
        self._fmu_instance.freeInstance()
        FMU2Simulator._logger.debug("        ->> removing extracted files...")
        shutil.rmtree(self._simulation_config.unzip_dir())
        FMU2Simulator._logger.debug("Clearing FMUSimulatorV2...finished")
        self._is_cleared = True

    @override
    def on_app_shutdown(self) -> None:
        if not self._is_cleared:
            self.clear()
