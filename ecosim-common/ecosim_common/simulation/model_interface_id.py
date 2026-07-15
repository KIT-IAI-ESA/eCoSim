from dataclasses import dataclass
from typing import Any

from ecosim_common.simulation.interface_id import InterfaceId


@dataclass(frozen=True)
class ModelInterfaceId:
    model_name: str
    interface: InterfaceId

    @classmethod
    def of_json(cls, value: dict[str, Any]) -> "ModelInterfaceId":
        return ModelInterfaceId(
            model_name=value["model_name"],
            interface=value["interface"],
        )

    def __str__(self) -> str:
        return f"{self.model_name}#{self.interface}"
