import datetime
from abc import abstractmethod, ABC
from typing import Tuple, List

from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_server.measurement.measurement_entry import MeasurementEntry


class MeasurementRepository(ABC):

    @abstractmethod
    def add(self,
            values: Tuple[ProtocolInterfaceValue, ...],
            timestamp: datetime.datetime,
            ) -> None:
        pass

    @abstractmethod
    def all(self) -> List[MeasurementEntry]:
        pass
