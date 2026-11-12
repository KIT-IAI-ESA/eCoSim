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
