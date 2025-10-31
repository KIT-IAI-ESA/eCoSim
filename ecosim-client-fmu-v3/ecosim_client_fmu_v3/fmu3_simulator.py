from __future__ import annotations
import shutil
from typing import override, List, Tuple, Any

import fmpy.fmi3

from ecosim_client_fmu_v3.fmu3_config import FMU3Config
from ecosim_client_fmu_v3.fmu3_simulator_config import FMU3SimulatorConfig
from ecosim_client_fmu_v3.fmu3_variable_type import FMU3VariableType
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue, InterfaceValueType
from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


class FMU3Simulator(ShutdownListener):
    _logger = ESPLogger("FMUSimulatorV3")

    @classmethod
    def of(
        cls,
        simulator_name: str,
        fmu_config: FMU3Config,
        execution_config: ExecutionConfig,
    ) -> FMU3Simulator:
        simulator_config: FMU3SimulatorConfig = FMU3SimulatorConfig.of(
            simulator_name=simulator_name,
            fmu_config=fmu_config,
        )
        return FMU3Simulator(
            simulation_config=simulator_config,
            execution_config=execution_config,
            fmu_instance=simulator_config.create_fmu_instance(),
        )

    def __init__(
        self,
        simulation_config: FMU3SimulatorConfig,
        execution_config: ExecutionConfig,
        fmu_instance: fmpy.fmi3.FMU3Slave,
    ) -> None:
        GlobalLogger.print_values(
            header="FMU CONFIG",
            value_pairs={
                "FMU instance": fmu_instance.instanceName,
                "FMI version": simulation_config.fmi_version(),
            },
        )
        self._simulation_config: FMU3SimulatorConfig = simulation_config
        self._execution_config: ExecutionConfig = execution_config
        self._fmu_instance: fmpy.fmi3.FMU3Slave = fmu_instance
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
            FMU3Simulator._logger.warning("Already initialized ... aborting second initialization.")
            return
        FMU3Simulator._logger.info(f"Initializing with start_time {start_time}")
        self._start_time = start_time
        self._fmu_instance.instantiate()
        self._fmu_instance.enterInitializationMode(startTime=start_time)
        self._fmu_instance.exitInitializationMode()
        self._is_initialized = True
        self._current_simulation_time = start_time
        FMU3Simulator._logger.debug("Initializing... finished.")

    def set_input_float(
        self,
        name: str,
        value: InterfaceValueType,
    ) -> None:
        if not isinstance(value, (float, int, complex)):
            raise TypeError(f"Expected a float but got {type(value)}.")
        FMU3Simulator._logger.debug(f"Setting float input {name} to {value}")
        self._fmu_instance.setFloat64([self._simulation_config.input_value_references(name)], [value])

    def set_input_float_matrix(
        self,
        name: str,
        value: InterfaceValueType,
    ) -> None:
        if not isinstance(value, list):
            raise TypeError(f"Expected a list but got {type(value)}.")
        FMU3Simulator._logger.debug(f"Setting float vector input {name} to {value}")
        self._fmu_instance.setFloat64([self._simulation_config.input_value_references(name)], value)

    def set_input_string(
        self,
        name: str,
        value: str,
    ) -> None:
        FMU3Simulator._logger.debug(f"Setting string input {name} to {value}")
        self._fmu_instance.setString([self._simulation_config.input_value_references(name)], [value])

    def set_input_boolean(
        self,
        name: str,
        value: bool,
    ) -> None:
        FMU3Simulator._logger.debug(f"Setting bool input {name} to {value}")
        self._fmu_instance.setBoolean([self._simulation_config.input_value_references(name)], [value])

    def get_output(
        self,
        name: str,
    ) -> InterfaceValueType:
        var_type = self._simulation_config.output_type(name)
        if var_type == FMU3VariableType.Float64:
            return self.get_output_float(name)
        elif var_type == FMU3VariableType.Float64Matrix:
            return self.get_output_float_matrix(name)  # type: ignore # mypy cannot correctly verify the type
        raise RuntimeError(f"Unsupported output type {var_type}")

    def get_output_float(
        self,
        name: str,
    ) -> float:
        value: float = self._fmu_instance.getFloat64([self._simulation_config.output_value_references(name)])[0]
        FMU3Simulator._logger.debug(f"Getting float output {name}: {value}")
        return value

    def get_output_float_matrix(
        self,
        name: str,
        m_dimension: int | None = None,
        n_dimension: int | None = None,
    ) -> List[float]:
        dimension = self._matrix_dimension(name, m_dimension, n_dimension)
        value: List[float] = self._fmu_instance.getFloat64([self._simulation_config.output_value_references(name)], dimension[0] * dimension[1])
        FMU3Simulator._logger.debug(f"Getting matrix[{m_dimension}x{n_dimension}] output {name}: {value}")
        return value

    def _matrix_dimension(
        self,
        name: str,
        default_m: int | None = None,
        default_n: int | None = None,
    ) -> Tuple[int, int]:
        m_dimension = default_m
        n_dimension = default_n
        if not m_dimension:
            config = self._simulation_config.output_matrix_config(name)
            m_dimension = config.fix_m() or self._get_any_int(config.m_value_reference, config.m_type)
            n_dimension = n_dimension or config.fix_n() or self._get_any_int(config.n_value_reference, config.n_type)
        return m_dimension, n_dimension or 1

    def _get_any_int(
        self,
        value_reference: Any,
        variable_type: str | None,
    ) -> int:
        type_getters = {
            'Int8': self._fmu_instance.getInt8,
            'Int16': self._fmu_instance.getInt16,
            'Int32': self._fmu_instance.getInt32,
            'Int64': self._fmu_instance.getInt64,
            'UInt8': self._fmu_instance.getUInt8,
            'UInt16': self._fmu_instance.getUInt16,
            'UInt32': self._fmu_instance.getUInt32,
            'UInt64': self._fmu_instance.getUInt64,
        }
        if variable_type in type_getters:
            return type_getters[variable_type]([value_reference])[0]  # type: ignore
        else:
            raise ValueError(f"Variable {value_reference} is not an integer type (found: {variable_type})")

    def get_output_string(
        self,
        name: str,
    ) -> str:
        value: str = self._fmu_instance.getString([self._simulation_config.output_value_references(name)])
        FMU3Simulator._logger.debug(f"Getting string output {name}: {value}")
        return value

    def server_used_output_values(self) -> ClientSimStepData:
        return ClientSimStepData.of_protocol_interface_values([
            ProtocolInterfaceValue(
                name=interface_name,
                value=self.get_output(interface_name),
            )
            for interface_name in self._execution_config.server_used_outputs()
        ])

    def get_output_boolean(
        self,
        name: str,
    ) -> bool:
        value: bool = self._fmu_instance.getBoolean([self._simulation_config.output_value_references(name)])
        FMU3Simulator._logger.debug(f"Getting bool output {name}: {value}")
        return value

    def do_step(
        self,
        input_values: dict[InterfaceId, InterfaceValueType],
        step_size_in_seconds: float,
    ) -> None:
        for interface_id, value in input_values.items():
            if isinstance(value, list):
                self.set_input_float_matrix(interface_id, value)
            else:
                self.set_input_float(interface_id, value)
        FMU3Simulator._logger.info(
            f"Executing next step (current_simulation_time={self._current_simulation_time} | step_size={step_size_in_seconds})...",
        )
        self._fmu_instance.doStep(
            currentCommunicationPoint=self._current_simulation_time,
            communicationStepSize=step_size_in_seconds,
        )
        self._current_simulation_time += step_size_in_seconds
        FMU3Simulator._logger.info(
            f"Executing next step finished (current_simulation_time={self._current_simulation_time}).",
        )

    def clear(self) -> None:
        if self._is_cleared:
            FMU3Simulator._logger.warning("Already cleared ... aborting second clearing.")
            return
        FMU3Simulator._logger.info("Clearing FMUSimulatorV3...")
        FMU3Simulator._logger.debug("        ->> terminating instance...")
        self._fmu_instance.terminate()
        FMU3Simulator._logger.debug("        ->> freeing instance...")
        self._fmu_instance.freeInstance()
        FMU3Simulator._logger.debug("        ->> removing extracted files...")
        shutil.rmtree(self._simulation_config.unzip_dir)
        FMU3Simulator._logger.debug("Clearing FMUSimulatorV3...finished")
        self._is_cleared = True

    @override
    def on_app_shutdown(self) -> None:
        if not self._is_cleared:
            self.clear()
