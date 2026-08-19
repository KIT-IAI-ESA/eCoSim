from dataclasses import dataclass, field
from datetime import datetime
from typing import override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.structures.esp_list import ESPList, ThreadESPList
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType


@dataclass(frozen=True)
class ServerTimeMeasurementRepositoryInMemory(ServerTimeMeasurementRepository):
    _measurements: ESPList[ServerTimeMeasurement] = field(default_factory=lambda: ThreadESPList[ServerTimeMeasurement]())

    @staticmethod
    def for_communication_protocol(protocol: CommunicationProtocol) -> "ServerTimeMeasurementRepositoryInMemory":
        return ServerTimeMeasurementRepositoryInMemory(
            _measurements=ESPList.of_type(
                list_type=ESPStructureType.THREAD if protocol == CommunicationProtocol.TCP_SOCKET else ESPStructureType.DASK_VARIABLE,
            ),
        )

    @override
    def put(
        self,
        server_time_measurement: ServerTimeMeasurement,
    ) -> None:
        with self._measurements.transaction() as current_measurements:
            if len(current_measurements) == 0:
                current_measurements.append(server_time_measurement)
                return

    @override
    def get_start(self, type: ServerTimeMeasurementType) -> datetime | None:
        measurement = self._measurements[0].get(type)
        return measurement.start_time if measurement is not None else None

    @override
    def get_end(self, type: ServerTimeMeasurementType) -> datetime | None:
        measurement = self._measurements[0].get(type)
        return measurement.end_time if measurement is not None else None
