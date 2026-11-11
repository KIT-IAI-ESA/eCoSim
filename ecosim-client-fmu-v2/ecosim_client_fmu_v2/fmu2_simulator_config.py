from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Dict
from uuid import uuid4

import fmpy
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_common_fmpy.tech.read_model_description import read_model_description
from fmpy.fmi2 import FMU2Slave
from fmpy.model_description import ModelDescription


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
        fmu_config: FMUBaseConfig,
        interface_names: list[str],
    ) -> FMU2SimulatorConfig:
        model_description = cls.read_model_description(fmu_config)
        # before extracting, so a rejected FMU leaves no files behind
        cls._ensure_interfaces_are_real(model_description=model_description, interface_names=interface_names)

        input_variables = [v for v in model_description.modelVariables if v.causality == "input"]
        output_variables = [v for v in model_description.modelVariables if v.causality == "output"]
        unzip_dir = fmpy.extract(fmu_config.fmu_file)
        return FMU2SimulatorConfig(
            _simulator_name=simulator_name,
            _model_description=model_description,
            _input_value_references={var.name: var.valueReference for var in input_variables},
            _output_value_references={var.name: var.valueReference for var in output_variables},
            _unzip_dir=unzip_dir,
            _fmu_file=fmu_config.fmu_file,
        )

    @staticmethod
    def _ensure_interfaces_are_real(model_description: ModelDescription, interface_names: list[str]) -> None:
        not_real = [
            f"{variable.name} ({variable.type})"
            for variable in model_description.modelVariables
            if variable.name in interface_names and variable.type != "Real"
        ]
        if not_real:
            raise TypeError(f"FMUv2 can only handle Real variables, but these interfaces are not Real: {', '.join(not_real)}")

    @classmethod
    def read_model_description(cls, fmu_config: FMUBaseConfig) -> ModelDescription:
        try:
            return read_model_description(file=fmu_config.fmu_file)
        except Exception as first_exception:
            nano_seconds = time.time_ns()
            today = datetime.now()
            temp_dir_name = f"{today.strftime('%Y-%m-%d %H:%M:%S')}.{nano_seconds % 1_000_000_000:09d}"
            # For identifying FMUs that throw XMLParseErrors
            FMU2SimulatorConfig._logger.warning("Model failed to read initially with '%s'. Trying to reload model description.", first_exception)
            for i in range(2):
                try:
                    importlib.reload(fmpy)
                    return read_model_description(file=fmu_config.fmu_file)
                except Exception as inner_exception:
                    unzip_dir = fmpy.extract(str(fmu_config.fmu_file), unzipdir=f"./failed_fmus/{temp_dir_name}")
                    FMU2SimulatorConfig._logger.debug("Reading modelDescription.xml directly from %s", unzip_dir)
                    try:
                        importlib.reload(fmpy)
                        return read_model_description(file=f"./failed_fmus/{temp_dir_name}/modelDescription.xml")
                    except Exception:
                        FMU2SimulatorConfig._logger.warning("Failed to read modelDescription.xml on %s. Exception: %s", i + 1, inner_exception)
            raise first_exception

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
