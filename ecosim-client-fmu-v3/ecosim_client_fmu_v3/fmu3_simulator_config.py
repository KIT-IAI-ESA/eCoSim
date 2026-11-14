from __future__ import annotations

import dataclasses
import math
from typing import Any, ClassVar, Dict
from uuid import uuid4

import fmpy
from ecosim_client_fmu_v3.fmu3_variable_type import FMU3VariableType
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_common_fmpy.tech.read_model_description import read_model_description
from fmpy.fmi3 import FMU3Slave
from fmpy.model_description import ModelDescription, ScalarVariable


@dataclasses.dataclass(frozen=True)
class FMU3SimulatorConfig:
    _logger: ClassVar[ESPLogger] = ESPLogger("SimulationConfig")

    simulator_name: str
    unzip_dir: str
    _fmu_config: FMUBaseConfig
    _model_description: ModelDescription
    _input_scalar_by_name: Dict[str, ScalarVariable]
    _output_scalar_by_name: Dict[str, ScalarVariable]

    @classmethod
    def of(
        cls,
        simulator_name: str,
        fmu_config: FMUBaseConfig,
        input_names: list[str],
        output_names: list[str],
    ) -> FMU3SimulatorConfig:
        model_description = read_model_description(file=fmu_config.fmu_file)
        fmu_config.ensure_model_runs_interfaces(
            model_description=model_description,
            input_names=input_names,
            output_names=output_names,
            fmi_major_version=3,
        )
        input_variables = [v for v in model_description.modelVariables if v.causality == "input"]
        output_variables = [v for v in model_description.modelVariables if v.causality == "output"]
        return FMU3SimulatorConfig(
            simulator_name=simulator_name,
            unzip_dir=fmpy.extract(fmu_config.fmu_file),
            _fmu_config=fmu_config,
            _model_description=model_description,
            _input_scalar_by_name={var.name: var for var in input_variables},
            _output_scalar_by_name={var.name: var for var in output_variables},
        )

    def reason_the_model_cannot_run(self, server_interface_settings: ServerInterfaceSettings) -> str | None:
        return self._fmu_config.reason_the_model_cannot_run(
            model_description=self._model_description,
            input_names=server_interface_settings.inputs,
            output_names=server_interface_settings.outputs,
            fmi_major_version=3,
        )

    def is_fmi_version(
        self,
        version: str,
    ) -> bool:
        return self._model_description.fmiVersion == version  # type: ignore

    def model_name(self) -> str:
        return self._model_description.modelName  # type: ignore

    def model_description(self) -> str:
        return self._model_description.description  # type: ignore

    def model_guid(self) -> str:
        return self._model_description.guid  # type: ignore

    def model_identifier(self) -> str:
        return self._model_description.coSimulation.modelIdentifier  # type: ignore

    def input_value_references(
        self,
        name: str,
    ) -> Any:
        return self._input_scalar_by_name[name].valueReference

    def output_value_references(
        self,
        name: str,
    ) -> Any:
        return self._output_scalar_by_name[name].valueReference

    def output_type(
        self,
        name: str,
    ) -> FMU3VariableType:
        return FMU3VariableType.type_of(self._output_scalar_by_name[name])

    def input_value_count(
        self,
        name: str,
    ) -> int:
        return math.prod(self._input_scalar_by_name[name].shape)

    def output_value_count(
        self,
        name: str,
    ) -> int:
        return math.prod(self._output_scalar_by_name[name].shape)

    def fmi_version(self) -> str | None:
        return self._model_description.fmiVersion  # type: ignore

    def create_fmu_instance(self) -> FMU3Slave:
        return FMU3Slave(
            guid=self.model_guid(),
            unzipDirectory=self.unzip_dir,
            modelIdentifier=self.model_identifier(),
            instanceName=str(uuid4()),
        )
