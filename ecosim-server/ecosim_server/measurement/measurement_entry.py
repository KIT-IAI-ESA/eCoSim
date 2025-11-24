import dataclasses
import datetime
from typing import Tuple

from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
)


@dataclasses.dataclass
class MeasurementEntry:
    values: Tuple[ProtocolInterfaceValue, ...]
    timestamp: datetime.datetime
