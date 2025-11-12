from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import List, override, Any, Dict

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
)
from ecosim_common.tech.datetime.date_time_to_millis import (
    date_time_to_millis_since_unix_epoch,
    millis_since_unix_epoch_to_date_time,
)


@dataclass(frozen=True)
class SimulationStepBatchRequest(MessageData):
    step_size_ms: int
    inputs: dict[datetime.datetime, List[ProtocolInterfaceValue]]

    @classmethod
    @override
    def of_json(
        cls,
        value: Dict[str, Any],
    ) -> SimulationStepBatchRequest:
        raw_inputs = value.get("inputs", {})
        parsed_inputs: dict[datetime.datetime, List[ProtocolInterfaceValue]] = {
            millis_since_unix_epoch_to_date_time(date_time): [
                ProtocolInterfaceValue(
                    name=interface_value["name"],
                    value=interface_value["value"],
                )
                for interface_value in interface_values
            ]
            for date_time, interface_values in raw_inputs.items()
        }

        return SimulationStepBatchRequest(
            step_size_ms=value["step_size_ms"],
            inputs=parsed_inputs,
        )

    @override
    def to_json(self) -> Dict[str, Any]:
        return {
            "step_size_ms": self.step_size_ms,
            "inputs": {
                date_time_to_millis_since_unix_epoch(dt): [
                    interface_value.to_json() for interface_value in interface_values
                ]
                for dt, interface_values in self.inputs.items()
            },
        }
