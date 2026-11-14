from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.close_name import closest_name
from fmpy.model_description import ModelDescription

from ecosim_common_fmpy.config.start_values import StartValues


@dataclass(frozen=True)
class FMUBaseConfig:
    fmu_file: Path
    start_value_texts: dict[str, str] = field(default_factory=dict)

    @classmethod
    def of_config_parser(
        cls,
        config_parser: ConfigParser,
    ) -> FMUBaseConfig:
        fmu_file = (config_parser.config_file.parent / config_parser.get_string_array("fmu", "fmu_file")[0]).absolute()
        return FMUBaseConfig(
            fmu_file=fmu_file,
            start_value_texts=StartValues.texts_of(config_parser),
        )

    @staticmethod
    def supported_type(fmi_major_version: int) -> str:
        """The one variable type the FMU clients exchange."""
        return "Real" if fmi_major_version == 2 else "Float64"

    def as_string(self) -> str:
        """The [fmu] section of an ini file next to the FMU, without the start values."""
        return f"[fmu]\nfmu_file = [{self.fmu_file.name}]"

    def start_values(self, model_description: ModelDescription, input_names: list[str]) -> StartValues:
        return StartValues.of_texts(
            texts=self.start_value_texts,
            model_description=model_description,
            input_names=input_names,
            fmu_file=self.fmu_file,
        )

    def reason_the_model_cannot_run(
        self,
        model_description: ModelDescription,
        input_names: list[str],
        output_names: list[str],
        fmi_major_version: int,
    ) -> str | None:
        try:
            self.ensure_model_runs_interfaces(
                model_description=model_description,
                input_names=input_names,
                output_names=output_names,
                fmi_major_version=fmi_major_version,
            )
        except (ValueError, TypeError) as error:
            return f"The simulation config does not fit the model. {error}"
        return None

    def ensure_model_runs_interfaces(
        self,
        model_description: ModelDescription,
        input_names: list[str],
        output_names: list[str],
        fmi_major_version: int,
    ) -> None:
        self.ensure_fmu_is_supported(
            model_description=model_description,
            interface_names=[*input_names, *output_names],
            fmi_major_version=fmi_major_version,
        )
        self.ensure_interfaces_exist(model_description=model_description, input_names=input_names, output_names=output_names)

    def ensure_interfaces_exist(self, model_description: ModelDescription, input_names: list[str], output_names: list[str]) -> None:
        missing_inputs, missing_outputs = FMUBaseConfig.missing_interfaces(
            model_description=model_description,
            input_names=input_names,
            output_names=output_names,
        )
        if not missing_inputs and not missing_outputs:
            return
        missing = [f"no {kind} {', '.join(names)}" for kind, names in (("input", missing_inputs), ("output", missing_outputs)) if names]
        hints = _hints(
            missing_inputs=missing_inputs,
            missing_outputs=missing_outputs,
            fmu_inputs=_variable_names(model_description=model_description, causality="input"),
            fmu_outputs=_variable_names(model_description=model_description, causality="output"),
        )
        raise ValueError(" ".join([f"The FMU {self.fmu_file} has {' and '.join(missing)}.", *hints]))

    @staticmethod
    def missing_interfaces(model_description: ModelDescription, input_names: list[str], output_names: list[str]) -> tuple[list[str], list[str]]:
        """The inputs and the outputs that the FMU does not have."""
        fmu_inputs = _variable_names(model_description=model_description, causality="input")
        fmu_outputs = _variable_names(model_description=model_description, causality="output")
        return [name for name in input_names if name not in fmu_inputs], [name for name in output_names if name not in fmu_outputs]

    def ensure_fmu_is_supported(self, model_description: ModelDescription, interface_names: list[str], fmi_major_version: int) -> None:
        if model_description.fmiMajorVersion != fmi_major_version:
            raise ValueError(
                f"The FMU {self.fmu_file} is FMI {model_description.fmiVersion}, but this client runs FMI {fmi_major_version} FMUs only.",
            )
        supported_type = FMUBaseConfig.supported_type(fmi_major_version=fmi_major_version)
        other_types = [
            f"{variable.name} ({variable.type})"
            for variable in model_description.modelVariables
            if variable.name in interface_names and variable.type != supported_type
        ]
        if other_types:
            raise TypeError(
                f"The FMU {self.fmu_file} is FMI {model_description.fmiVersion}, which eCoSim supports with {supported_type} variables only, "
                + f"but these interfaces are not {supported_type}: {', '.join(other_types)}.",
            )


def _variable_names(model_description: ModelDescription, causality: str) -> list[str]:
    return [variable.name for variable in model_description.modelVariables if variable.causality == causality]


def _hints(missing_inputs: list[str], missing_outputs: list[str], fmu_inputs: list[str], fmu_outputs: list[str]) -> list[str]:
    several_missing = len(missing_inputs) + len(missing_outputs) > 1
    hints = [
        _hint(name=name, same_kind=fmu_inputs, other_kind=fmu_outputs, other_kind_text="an output", several_missing=several_missing)
        for name in missing_inputs
    ]
    hints += [
        _hint(name=name, same_kind=fmu_outputs, other_kind=fmu_inputs, other_kind_text="an input", several_missing=several_missing)
        for name in missing_outputs
    ]
    return [hint for hint in hints if hint]


def _hint(name: str, same_kind: list[str], other_kind: list[str], other_kind_text: str, several_missing: bool) -> str:
    if name in other_kind:
        return f"{name} is {other_kind_text} of the FMU."
    closest = closest_name(name=name, known_names=same_kind)
    if closest is None:
        return ""
    return f"Did you mean {closest} instead of {name}?" if several_missing else f"Did you mean {closest}?"
