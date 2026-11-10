from __future__ import annotations

import shutil
from dataclasses import dataclass
from typing import Any, List, Tuple

import fmpy
from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.renderer.pre_rendered_images_service import PreRenderedImageService
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from typing_extensions import override

from ecosim_client_fmu_v3.fmu3_simulator_config import FMU3SimulatorConfig
from ecosim_client_fmu_v3.fmu3_variable_type import FMU3VariableType


@dataclass(kw_only=True)
class FMU3Client(SimulatorClient):
    _simulation_config: FMU3SimulatorConfig
    _fmu_instance: fmpy.fmi3.FMU3Slave

    @staticmethod
    def of(
        config_parser: ConfigParser,
        config_override: ClientConfigOverride | None = None,
    ) -> FMU3Client:
        client_config = SimpleClientConfig.of_config_parser(config_parser, config_override)
        simulator_config = FMU3SimulatorConfig.of(
            fmu_config=FMUBaseConfig.of_config_parser(config_parser),
            simulator_name=client_config.simulator_config().simulator_name,
        )
        return FMU3Client(
            _client_config=client_config,
            _simulation_config=simulator_config,
            _fmu_instance=simulator_config.create_fmu_instance(),
            _image_renderer_service=PreRenderedImageService.of_config_path(config_parser.config_file),
        )

    @override
    def _on_initialize_model(
        self,
        start_time: float = 0.0,
    ) -> None:
        self._fmu_instance.instantiate()
        self._fmu_instance.enterInitializationMode(startTime=start_time)
        self._fmu_instance.exitInitializationMode()

    @override
    def _set_input_float(
        self,
        name: str,
        value: float | None,
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._fmu_instance.setFloat64([self._simulation_config.input_value_references(name)], [value])

    @override
    def _set_input_float_matrix(
        self,
        name: str,
        value: FloatMatrix,
    ) -> None:
        self.logger.debug("Setting float vector input %s to %s", name, value)
        self._fmu_instance.setFloat64([self._simulation_config.input_value_references(name)], value)

    @override
    def _get_model_output(
        self,
        name: str,
    ) -> InterfaceValue:
        var_type = self._simulation_config.output_type(name)
        if var_type == FMU3VariableType.Float64:
            return self._get_output_float(name)
        elif var_type == FMU3VariableType.Float64Matrix:
            return self._get_output_float_matrix(name)  # type: ignore # mypy cannot correctly verify the type
        raise RuntimeError(f"Unsupported output type {var_type}")

    def _get_output_float(
        self,
        name: str,
    ) -> float:
        value: float = self._fmu_instance.getFloat64([self._simulation_config.output_value_references(name)])[0]
        self.logger.debug("Getting float output %s: %s", name, value)
        return value

    def _get_output_float_matrix(
        self,
        name: str,
        m_dimension: int | None = None,
        n_dimension: int | None = None,
    ) -> List[float]:
        dimension = self._matrix_dimension(name, m_dimension, n_dimension)
        value: List[float] = self._fmu_instance.getFloat64([self._simulation_config.output_value_references(name)], dimension[0] * dimension[1])
        self.logger.debug("Getting matrix[%sx%s] output %s: %s", m_dimension, n_dimension, name, value)
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
            "Int8": self._fmu_instance.getInt8,
            "Int16": self._fmu_instance.getInt16,
            "Int32": self._fmu_instance.getInt32,
            "Int64": self._fmu_instance.getInt64,
            "UInt8": self._fmu_instance.getUInt8,
            "UInt16": self._fmu_instance.getUInt16,
            "UInt32": self._fmu_instance.getUInt32,
            "UInt64": self._fmu_instance.getUInt64,
        }
        if variable_type in type_getters:
            return type_getters[variable_type]([value_reference])[0]  # type: ignore
        else:
            raise ValueError(f"Variable {value_reference} is not an integer type (found: {variable_type})")

    @override
    def _on_do_step(
        self,
        step_size_in_seconds: float,
    ) -> None:
        self._fmu_instance.doStep(
            currentCommunicationPoint=self._current_simulation_time,
            communicationStepSize=step_size_in_seconds,
        )

    @override
    def _on_clear_simulator(self) -> None:
        try:
            # the FMU is extracted on creation, but only instantiated when the simulation starts
            if self._is_initialized:
                self.logger.debug("        ->> terminating instance...")
                self._fmu_instance.terminate()
        finally:
            self._free_fmu_instance()
            self.logger.debug("        ->> removing extracted files...")
            shutil.rmtree(self._simulation_config.unzip_dir, ignore_errors=True)

    def _free_fmu_instance(self) -> None:
        self.logger.debug("        ->> freeing instance...")
        try:
            self._fmu_instance.freeInstance()
        except Exception:
            self.logger.exception("Freeing the FMU instance failed.")
