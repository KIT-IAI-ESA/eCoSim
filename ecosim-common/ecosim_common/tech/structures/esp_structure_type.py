from __future__ import annotations

from enum import Enum
from typing import assert_never

from ecosim_common.communication.communication_protocol import CommunicationProtocol


class ESPStructureType(Enum):
    DASK_VARIABLE = "dask_variable"
    THREAD = "thread"
    SIMPLE = "simple"

    @staticmethod
    def default_for_communication_protocol(communication_protocol: CommunicationProtocol) -> ESPStructureType:
        match communication_protocol:
            case CommunicationProtocol.TCP_SOCKET:
                return ESPStructureType.THREAD
            case CommunicationProtocol.DASK:
                return ESPStructureType.DASK_VARIABLE
            case _:
                assert_never(communication_protocol)
