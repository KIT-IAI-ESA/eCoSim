from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.close_name import closest_name
from fmpy.model_description import ModelDescription, ModelVariable

from ecosim_common_fmpy.config.start_value import StartValue

START_VALUES_SECTION = "start_values"


@dataclass(frozen=True)
class StartValues:
    values: list[StartValue]

    @staticmethod
    def texts_of(config_parser: ConfigParser) -> dict[str, str]:
        """The [start_values] section as written, after a check for a misspelt section name."""
        # a misspelt section would be ignored without a word, like every unknown section
        misspelt = [
            section
            for section in config_parser.sections()
            if section != START_VALUES_SECTION and closest_name(name=section.lower(), known_names=[START_VALUES_SECTION], cutoff=0.8) is not None
        ]
        if misspelt:
            raise ValueError(f"{config_parser.config_file} has a section [{misspelt[0]}]. Did you mean [{START_VALUES_SECTION}]?")
        return config_parser.get_section(START_VALUES_SECTION)

    @staticmethod
    def of_texts(texts: dict[str, str], model_description: ModelDescription, input_names: list[str], fmu_file: Path) -> StartValues:
        """Checks every value before the FMU is extracted, and names all problems at once."""
        results = _start_values_or_problems(texts=texts, model_description=model_description, input_names=input_names)
        problems = [f"  {name}: {result}" for name, result in results.items() if isinstance(result, str)]
        if problems:
            raise ValueError("\n".join([f"The FMU {fmu_file} cannot take these start values:", *problems]))
        return StartValues(values=[result for result in results.values() if isinstance(result, StartValue)])

    @staticmethod
    def problems_of(texts: dict[str, str], model_description: ModelDescription, input_names: list[str]) -> list[str]:
        """One line per start value the FMU cannot take, for a check that lists every problem of a simulation."""
        results = _start_values_or_problems(texts=texts, model_description=model_description, input_names=input_names)
        return [f"{name}: {result}" for name, result in results.items() if isinstance(result, str)]

    def set_on(self, fmu_instance: Any) -> None:
        for start_value in self.values:
            start_value.set_on(fmu_instance)

    def as_lines(self) -> list[str]:
        return [start_value.as_line() for start_value in self.values]


def _start_values_or_problems(texts: dict[str, str], model_description: ModelDescription, input_names: list[str]) -> dict[str, StartValue | str]:
    variables = {variable.name: variable for variable in model_description.modelVariables}
    return {name: _start_value_or_problem(name=name, text=text, variables=variables, input_names=input_names) for name, text in texts.items()}


def _start_value_or_problem(name: str, text: str, variables: dict[str, ModelVariable], input_names: list[str]) -> StartValue | str:
    try:
        return StartValue.of_text(name=name, text=text, variables=variables, input_names=input_names)
    except ValueError as problem:
        return str(problem)
