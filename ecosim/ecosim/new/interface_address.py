from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class InterfaceAddress:
    """An input or an output of a model, written like house.T_out."""

    model: str
    name: str

    def __str__(self) -> str:
        return f"{self.model}.{self.name}"
