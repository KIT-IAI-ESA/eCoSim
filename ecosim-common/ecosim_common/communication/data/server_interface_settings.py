from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.simulation.interface_id import InterfaceId


@dataclass(frozen=True)
class ServerInterfaceSettings(MessageData):
    inputs: List[InterfaceId]
    outputs: List[InterfaceId]
