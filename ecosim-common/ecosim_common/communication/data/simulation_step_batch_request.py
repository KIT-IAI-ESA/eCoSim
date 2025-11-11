from __future__ import annotations

from dataclasses import dataclass
from typing import List, override, Any, Dict

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue


@dataclass(frozen=True)
class SimulationStepBatchRequest(MessageData):
    step_start: int
    step_end: int
    step_size_ms: int
    inputs: dict[int, List[ProtocolInterfaceValue]]

    @classmethod
    @override
    def of_json(
        cls,
        value: Dict[str, Any],
    ) -> SimulationStepBatchRequest:
        raw_inputs = value.get('inputs', {})
        parsed_inputs: dict[int, List[ProtocolInterfaceValue]] = {
            int(step): [
                ProtocolInterfaceValue(
                    name=interface_value['name'],
                    value=interface_value['value'],
                )
                for interface_value in interface_values
            ]
            for step, interface_values in raw_inputs.items()
        }

        return SimulationStepBatchRequest(
            step_start=value['step_start'],
            step_end=value['step_end'],
            step_size_ms=value['step_size_ms'],
            inputs=parsed_inputs,
        )
