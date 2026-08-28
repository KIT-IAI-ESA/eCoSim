from __future__ import annotations

from dataclasses import dataclass
from typing import List, override, Any, Dict

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue


@dataclass(frozen=True)
class SimulationStepRequest(MessageData):
    step: int
    inputs: List[ProtocolInterfaceValue]

    @classmethod
    @override
    def of_json(
        cls,
        value: Dict[str, Any],
    ) -> SimulationStepRequest:
        return SimulationStepRequest(
            step=value["step"],
            inputs=[
                ProtocolInterfaceValue(
                    name=interface_value["name"],
                    value=interface_value["value"],
                )
                for interface_value in value["inputs"]
            ],
        )
