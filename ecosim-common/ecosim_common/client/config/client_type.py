from __future__ import annotations

from enum import Enum
from typing import List, Tuple


class ClientType(Enum):
    FMU_2 = ("fmu_2", ("fmu", "fmu2"))
    FMU_3 = ("fmu_3", ("fmu3",))
    Matlab = "matlab"
    Pyro5 = ("pyro5", ("pyro",))

    def __init__(
        self,
        serialized: str,
        alternatives: Tuple[str] | None = None,
    ):
        self.serialized: str = serialized
        self._matches_internal: List[str] = [self.serialized]
        if alternatives is not None:
            for alternative in alternatives:
                self._matches_internal.append(alternative.lower())

    @classmethod
    def of_string(
        cls,
        type: str,
    ) -> ClientType:
        if ClientType.FMU_2.matches_string(type):
            return ClientType.FMU_2
        if ClientType.FMU_3.matches_string(type):
            return ClientType.FMU_3
        if ClientType.Matlab.matches_string(type):
            return ClientType.Matlab
        if ClientType.Pyro5.matches_string(type):
            return ClientType.Pyro5
        raise TypeError(f"Unknown client type {type}")

    def matches_string(
        self,
        source: str,
    ) -> bool:
        return source.lower() in self._matches_internal
