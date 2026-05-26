from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, ClassVar
from uuid import uuid4

import fmpy
from fmpy.fmi2 import FMU2Slave
from fmpy.model_description import ModelDescription

from ecosim_client_fmu_v2.fmu2_config import FMU2Config
from ecosim_common.tech.logger.logger import ESPLogger


@dataclass(frozen=True)
class FMU2SimulatorConfig:
    _logger: ClassVar[ESPLogger] = ESPLogger("SimulationConfig")

    _fmu_file: Path
    _model_description: ModelDescription
    _unzip_dir: str
    _input_value_references: Dict[str, Any]
    _output_value_references: Dict[str, Any]
    _simulator_name: str

    @classmethod
    def of(
        cls,
        simulator_name: str,
        fmu_config: FMU2Config,
    ) -> FMU2SimulatorConfig:
        try:
            model_description = fmpy.read_model_description(str(fmu_config.fmu_file))
        except Exception as e:
            # For identifying FMUs that throw XMLParseErrors
            unzip_dir = fmpy.extract(str(fmu_config.fmu_file), unzipdir="./failed_fmus/"+simulator_name)
            FMU2SimulatorConfig._logger.error(str(e))
            FMU2SimulatorConfig._logger.error(f"HERE IS THE UNZIP_DIR FOR THE FAIL: {unzip_dir}")
            raise

        input_variables = [v for v in model_description.modelVariables if v.causality == 'input']
        output_variables = [v for v in model_description.modelVariables if v.causality == 'output']
        unzip_dir = fmpy.extract(fmu_config.fmu_file)
        return FMU2SimulatorConfig(
            _simulator_name=simulator_name,
            _model_description=model_description,
            _input_value_references={var.name: var.valueReference for var in input_variables},
            _output_value_references={var.name: var.valueReference for var in output_variables},
            _unzip_dir=unzip_dir,
            _fmu_file=fmu_config.fmu_file,
        )

    def is_fmi_version(
        self,
        version: str,
    ) -> bool:
        if self._model_description is None:
            FMU2SimulatorConfig._logger.error("No model description is set. Please investigate")
            return False
        return self._model_description.fmiVersion == version

    def model_name(self) -> str:
        return self._model_description.modelName

    def simulator_name(self) -> str:
        return self._simulator_name

    def model_description(self) -> str:
        return self._model_description.description

    def model_guid(self) -> str:
        return self._model_description.guid

    def model_identifier(self) -> str:
        return self._model_description.coSimulation.modelIdentifier

    def unzip_dir(self) -> str:
        return self._unzip_dir

    def input_value_references(
        self,
        name: str,
    ) -> str:
        return self._input_value_references[name]

    def output_value_references(
        self,
        name: str,
    ) -> str:
        return self._output_value_references[name]

    def fmi_version(self) -> str | None:
        return self._model_description.fmiVersion

    def create_fmu2_instance(self) -> FMU2Slave:
        return FMU2Slave(
            guid=self.model_guid(),
            unzipDirectory=self.unzip_dir(),
            modelIdentifier=self.model_identifier(),
            instanceName=str(uuid4()),
        )
