from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from ecosim_common.config.config_parser import ConfigParser, ConfigParserException
from ecosim_common.tech.close_name import did_you_mean
from fmpy.model_description import ModelVariable


@dataclass(frozen=True)
class StartValue:
    variable: ModelVariable
    value: float | int | bool

    @staticmethod
    def of_text(name: str, text: str, variables: dict[str, ModelVariable], input_names: list[str]) -> StartValue:
        variable = variables.get(name)
        if variable is None:
            raise ValueError(f"not a variable of the FMU.{did_you_mean(name=name, known_names=variables)}")
        _ensure_settable(variable=variable, input_names=input_names)
        _ensure_supported_type(variable)
        return StartValue(variable=variable, value=_parsed_value(variable=variable, text=text.strip()))

    def set_on(self, fmu_instance: Any) -> None:
        # fmpy has a setter per FMI type, with the parameters (vr, value) in FMI 2 and (vr, values) in FMI 3
        setter = getattr(fmu_instance, f"set{self.variable.type}")
        try:
            setter([self.variable.valueReference], [self.value])
        except Exception as error:
            raise RuntimeError(f"The FMU did not accept the start value {self.as_line()}") from error

    def as_line(self) -> str:
        value = str(self.value).lower() if isinstance(self.value, bool) else self.value
        return f"{self.variable.name} = {with_unit(variable=self.variable, value=value)}"


def with_unit(variable: ModelVariable, value: object) -> str:
    unit = unit_of(variable)
    return f"{value} {unit}" if unit else f"{value}"


def unit_of(variable: ModelVariable) -> str | None:
    unit = variable.unit or getattr(variable.declaredType, "unit", None)
    # "1" is the unit of a number without a unit
    return unit if unit != "1" else None


def _ensure_settable(variable: ModelVariable, input_names: list[str]) -> None:
    # FMI allows a set before the initialization only for initial exact or approx
    if variable.variability == "constant":
        raise ValueError("a constant of the FMU cannot be changed")
    if variable.causality == "independent":
        raise ValueError("the simulation time cannot be set")
    if variable.causality == "structuralParameter":
        raise ValueError("eCoSim cannot change a structural parameter")
    if variable.initial not in ("exact", "approx"):
        raise ValueError("a value calculated by the FMU cannot be set")
    if variable.name in input_names:
        raise ValueError("an input in the .fmc file gets a new value every step")


def _ensure_supported_type(variable: ModelVariable) -> None:
    if variable.shape:
        raise ValueError("an array, but [start_values] takes single values only")
    if variable.type not in ("Real", "Float32", "Float64", "Boolean") and not _is_integer(variable):
        raise ValueError(f"[start_values] does not support the type {variable.type}")


def _is_integer(variable: ModelVariable) -> bool:
    # FMI 2 has Integer, FMI 3 has Int8 to Int64 and UInt8 to UInt64
    return variable.type == "Integer" or variable.type.removeprefix("U") in ("Int8", "Int16", "Int32", "Int64")


def _parsed_value(variable: ModelVariable, text: str) -> float | int | bool:
    if not text:
        raise ValueError("no value after the =")
    if variable.type == "Boolean":
        return _parsed_boolean(text)
    number = _parsed_integer(variable=variable, text=text) if _is_integer(variable) else _parsed_float(text)
    _ensure_within_the_limits(variable=variable, number=number)
    return number


def _parsed_boolean(text: str) -> bool:
    try:
        return ConfigParser.config_string_to_bool(text)
    except ConfigParserException:
        raise ValueError(f"'{text}' is not true or false{_comment_hint(text)}") from None


def _parsed_integer(variable: ModelVariable, text: str) -> int:
    try:
        integer = int(text)
    except ValueError:
        raise ValueError(f"'{text}' is not a whole number{_comment_hint(text)}") from None
    _ensure_fits_the_type(variable=variable, integer=integer)
    return integer


def _parsed_float(text: str) -> float:
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"'{text}' is not a number{_comment_hint(text)}") from None
    if not math.isfinite(number):
        raise ValueError(f"'{text}' is not a finite number")
    return number


def _comment_hint(text: str) -> str:
    return ". Write a comment on its own line" if "#" in text or ";" in text else ""


def _ensure_fits_the_type(variable: ModelVariable, integer: int) -> None:
    # ctypes silently wraps a value that does not fit
    bits = 32 if variable.type == "Integer" else int(variable.type.removeprefix("U").removeprefix("Int"))
    lowest, highest = (0, 2**bits - 1) if variable.type.startswith("U") else (-(2 ** (bits - 1)), 2 ** (bits - 1) - 1)
    if not lowest <= integer <= highest:
        raise ValueError(f"{integer} does not fit into {variable.type} ({lowest} to {highest})")


def _ensure_within_the_limits(variable: ModelVariable, number: float) -> None:
    value = with_unit(variable=variable, value=number)
    minimum, maximum = _limit(variable=variable, attribute="min"), _limit(variable=variable, attribute="max")
    if minimum is not None and number < minimum:
        raise ValueError(f"{value} is below the minimum of the FMU, {with_unit(variable=variable, value=minimum)}")
    if maximum is not None and number > maximum:
        raise ValueError(f"{value} is above the maximum of the FMU, {with_unit(variable=variable, value=maximum)}")


def _limit(variable: ModelVariable, attribute: str) -> float | None:
    # a variable without its own limit has the limit of its declared type
    limit = getattr(variable, attribute) or getattr(variable.declaredType, attribute, None)
    return float(limit) if limit is not None else None
