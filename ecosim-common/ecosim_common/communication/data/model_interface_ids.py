from __future__ import annotations

from dataclasses import dataclass
from typing import List, override, Dict, Any

from ecosim_common.client.config.client_config import ClientConfig
from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.simulation.model_interface_id import ModelInterfaceId


@dataclass(frozen=True)
class ModelInterfaceIds(MessageData):
    interfaces: List[ModelInterfaceId]

    @classmethod
    @override
    def of_json(
        cls,
        value: Dict[str, Any],
    ) -> ModelInterfaceIds:
        return ModelInterfaceIds(
            interfaces=[ModelInterfaceId.of_json(interface) for interface in value['interfaces']],
        )

    @classmethod
    def of_interface_config(
        cls,
        config: ClientConfig,
    ) -> ModelInterfaceIds:
        return ModelInterfaceIds(
            interfaces=[
                ModelInterfaceId(
                    interface=interface.name,
                    model_name=config.meta_data().model_name,
                ) for interface in config.interfaces_config().interfaces
            ],
        )
