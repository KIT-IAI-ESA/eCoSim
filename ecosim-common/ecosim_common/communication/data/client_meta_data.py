from __future__ import annotations

from dataclasses import dataclass

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.config.client_id import ClientID


@dataclass(frozen=True)
class ClientMetaData(MessageData):
    version: str
    simulator_name: str
    model_name: str

    def client_id(self) -> ClientID:
        return ClientID(self.model_name, self.simulator_name)
