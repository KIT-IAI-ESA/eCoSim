from __future__ import annotations

from dataclasses import dataclass
from typing import List, override, Any, Dict

from ecosim_common.communication.channel.message_data import MessageData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue


@dataclass(frozen=True)
class ClientSimStepData(MessageData):

    interface_values: List[ProtocolInterfaceValue]

    @staticmethod
    def of_protocol_interface_values(interface_values: List[ProtocolInterfaceValue]) -> ClientSimStepData:
        return ClientSimStepData(interface_values)

    @classmethod
    @override
    def of_json(cls,
                value: Dict[str, Any],
                ) -> ClientSimStepData:
        return ClientSimStepData(
            interface_values=[ProtocolInterfaceValue.of_json(interface_value) for interface_value in value['interface_values']],
        )
