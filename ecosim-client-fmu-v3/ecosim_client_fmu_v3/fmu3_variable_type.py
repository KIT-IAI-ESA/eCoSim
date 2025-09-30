from __future__ import annotations
from enum import Enum

from fmpy.model_description import ScalarVariable


class FMU3VariableType(Enum):
    Float64 = "float64"
    Float64Matrix = "float64_matrix"

    @staticmethod
    def type_of(variable: ScalarVariable) -> FMU3VariableType:
        if variable.type.casefold() == "float64":
            if not variable.dimensions and not variable.dimensionValueReferences:
                return FMU3VariableType.Float64
            return FMU3VariableType.Float64Matrix
        raise RuntimeError(f"Unknown variable type: {variable.type}")
