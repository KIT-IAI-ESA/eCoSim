from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecosim_common.client.config.client_type import ClientType
from fmpy.model_description import ModelDescription, ModelVariable

from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_common_fmpy.config.simulator_client_type import client_type_of_fmi_version
from ecosim_common_fmpy.tech.read_model_description import read_model_description


@dataclass(frozen=True)
class FMUInterface:
    name: str
    unit: str
    description: str
    start: str | None
    shape: tuple[int, ...]

    @staticmethod
    def of_variable(variable: ModelVariable) -> FMUInterface:
        declared_unit = variable.declaredType.unit if variable.declaredType is not None else None
        return FMUInterface(
            name=variable.name,
            unit=variable.unit or declared_unit or "",
            description=variable.description or "",
            start=variable.start,
            shape=tuple(variable.shape),
        )


@dataclass(frozen=True)
class SkippedVariable:
    name: str
    causality: str
    type: str


@dataclass(frozen=True)
class FMUInterfaces:
    """The inputs and outputs of an FMU: those the FMU clients exchange, and the others."""

    fmu_file: Path
    fmi_version: str
    inputs: tuple[FMUInterface, ...]
    outputs: tuple[FMUInterface, ...]
    skipped: tuple[SkippedVariable, ...]

    @staticmethod
    def of_fmu_file(fmu_file: Path) -> FMUInterfaces:
        model_description = read_model_description(file=fmu_file)
        FMUInterfaces._ensure_a_client_runs_it(fmu_file=fmu_file, model_description=model_description)
        supported_type = FMUBaseConfig.supported_type(fmi_major_version=model_description.fmiMajorVersion)
        variables = [variable for variable in model_description.modelVariables if variable.causality in ("input", "output")]
        exchanged = [variable for variable in variables if variable.type == supported_type]
        return FMUInterfaces(
            fmu_file=fmu_file,
            fmi_version=model_description.fmiVersion,
            inputs=tuple(FMUInterface.of_variable(variable) for variable in exchanged if variable.causality == "input"),
            outputs=tuple(FMUInterface.of_variable(variable) for variable in exchanged if variable.causality == "output"),
            skipped=tuple(
                SkippedVariable(name=variable.name, causality=variable.causality, type=variable.type)
                for variable in variables
                if variable.type != supported_type
            ),
        )

    @staticmethod
    def _ensure_a_client_runs_it(fmu_file: Path, model_description: ModelDescription) -> None:
        # raises for an FMI version that no client runs
        client_type_of_fmi_version(fmi_version=model_description.fmiVersion, fmu_file=fmu_file)
        if model_description.coSimulation is None:
            raise ValueError(f"{fmu_file} has no co-simulation part. It is for model exchange only, and eCoSim runs co-simulation FMUs only.")

    def client_type(self) -> ClientType:
        return client_type_of_fmi_version(fmi_version=self.fmi_version, fmu_file=self.fmu_file)

    def input_named(self, name: str) -> FMUInterface | None:
        return next((interface for interface in self.inputs if interface.name == name), None)

    def output_named(self, name: str) -> FMUInterface | None:
        return next((interface for interface in self.outputs if interface.name == name), None)
