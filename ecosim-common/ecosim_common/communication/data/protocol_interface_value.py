from __future__ import annotations

from dataclasses import dataclass
from typing import List, Union

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.simulation.interface_id import InterfaceId

InterfaceValueType = Union[float, List["InterfaceValueType"], None]


@dataclass(frozen=True)
class ProtocolInterfaceValue(MessageData):
    name: InterfaceId
    value: InterfaceValueType


@dataclass
class ProtocolInterfaceValueMutable:
    name: InterfaceId
    value: InterfaceValueType = None

    def to_immutable(self) -> ProtocolInterfaceValue:
        return ProtocolInterfaceValue(self.name, self.value)
