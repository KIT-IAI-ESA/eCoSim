from __future__ import annotations

from dataclasses import dataclass

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.simulation.interface_id import InterfaceId

type FloatMatrix = list[float] | list[FloatMatrix]
type InterfaceValue = float | FloatMatrix | None


@dataclass(frozen=True)
class ProtocolInterfaceValue(MessageData):
    name: InterfaceId
    value: InterfaceValue


@dataclass
class ProtocolInterfaceValueMutable:
    name: InterfaceId
    value: InterfaceValue = None

    def to_immutable(self) -> ProtocolInterfaceValue:
        return ProtocolInterfaceValue(self.name, self.value)
