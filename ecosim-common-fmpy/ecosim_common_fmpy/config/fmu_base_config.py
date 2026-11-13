from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser
from fmpy.model_description import ModelDescription


@dataclass(frozen=True)
class FMUBaseConfig:
    fmu_file: Path

    @classmethod
    def of_config_parser(
        cls,
        config_parser: ConfigParser,
    ) -> FMUBaseConfig:
        fmu_file = (config_parser.config_file.parent / config_parser.get_string_array("fmu", "fmu_file")[0]).absolute()
        return FMUBaseConfig(
            fmu_file=fmu_file,
        )

    def ensure_interfaces_exist(self, model_description: ModelDescription, interface_names: list[str]) -> None:
        inputs_and_outputs = [variable.name for variable in model_description.modelVariables if variable.causality in ("input", "output")]
        missing = [name for name in interface_names if name not in inputs_and_outputs]
        if missing:
            raise ValueError(f"The FMU {self.fmu_file} has no input or output for these interfaces: {', '.join(missing)}")

    def ensure_fmu_is_supported(self, model_description: ModelDescription, interface_names: list[str], fmi_major_version: int) -> None:
        if model_description.fmiMajorVersion != fmi_major_version:
            raise ValueError(f"The FMU {self.fmu_file} is FMI {model_description.fmiVersion}, but this client runs FMI {fmi_major_version} FMUs only")
        supported_type = "Real" if fmi_major_version == 2 else "Float64"
        other_types = [
            f"{variable.name} ({variable.type})"
            for variable in model_description.modelVariables
            if variable.name in interface_names and variable.type != supported_type
        ]
        if other_types:
            raise TypeError(
                f"The FMU {self.fmu_file} is FMI {model_description.fmiVersion}, which eCoSim supports with {supported_type} variables only, "
                + f"but these interfaces are not {supported_type}: {', '.join(other_types)}",
            )
