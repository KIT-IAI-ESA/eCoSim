from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class InterfaceAddress:
    """An input or an output of a model, written like house.T_out."""

    model: str
    name: str

    @staticmethod
    def of_text(text: str, option_text: str) -> InterfaceAddress:
        # a model name has no dot, an interface name can have some, like weatherBus.TDryBul
        model, separator, name = text.partition(".")
        if not separator or not model or not name:
            raise ValueError(f"{option_text}: '{text}' names no interface. Write the model, a dot and the interface, like house.T_out")
        return InterfaceAddress(model=model, name=name)

    def __str__(self) -> str:
        return f"{self.model}.{self.name}"
