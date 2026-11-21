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
        interface: dict[str, Any],
        interface_type: InterfaceType,
    ) -> "ModelInterfaceClient":
        return ModelInterfaceClient(
            model_interface_id=model_interface_id,
            name=model_interface_id.interface,
            unit=interface.get("unit"),
            description=interface.get("description") or "",
            type=interface_type,
            required=config_parser.ConfigParser.config_bool_or_string_to_bool(
                value=interface.setdefault(
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
