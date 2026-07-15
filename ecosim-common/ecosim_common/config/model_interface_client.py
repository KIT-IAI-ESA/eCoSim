from dataclasses import dataclass
from typing import Any

from ecosim_common.config import config_parser
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_server import ModelInterfaceServer
from ecosim_common.simulation.model_interface_id import ModelInterfaceId


@dataclass
class ModelInterfaceClient:
    model_interface_id: ModelInterfaceId
    name: str
    unit: str | None
    description: str
    type: InterfaceType
    required: bool

    @staticmethod
    def of_json_client_config(
        model_interface_id: ModelInterfaceId,
        interface: dict[str, str],
        interface_type: InterfaceType,
    ) -> "ModelInterfaceClient":
        interface_name = interface.get("name")
        if not interface_name:
            raise RuntimeError(f"Interface name not found: {interface}")
        return ModelInterfaceClient(
            model_interface_id=model_interface_id,
            name=interface_name,
            unit=interface.get("unit"),
            description=interface.get("description") or "",
            type=interface_type,
            required=config_parser.ConfigParser.config_string_to_bool(
                interface.setdefault(
                    "required",
                    "false",
                ),
            ),
        )

    def __eq__(
        self,
        other: Any,
    ) -> bool:
        if isinstance(
            other,
            ModelInterfaceClient,
        ):
            return self.model_interface_id == other.model_interface_id
        return False

    def __repr__(self) -> str:
        return f"{self.model_interface_id} ({self.type})"

    def matches_server_interface(
        self,
        server_interface: ModelInterfaceServer,
    ) -> bool:
        return self.model_interface_id == server_interface.model_interface_id
