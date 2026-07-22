from dataclasses import dataclass, field

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.structures.esp_list import ESPList, ThreadESPList
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement


@dataclass(frozen=True)
class ServerTimeMeasurementRepositoryInMemory(ServerTimeMeasurementRepository):
    _measurements: ESPList[ServerTimeMeasurement] = field(default_factory=lambda: ThreadESPList[ServerTimeMeasurement]())

    @staticmethod
    def for_communication_protocol(protocol: CommunicationProtocol) -> "ServerTimeMeasurementRepositoryInMemory":
        return ServerTimeMeasurementRepositoryInMemory(
            _measurements=ESPList.of_type(
                list_type=ESPStructureType.THREAD if protocol == CommunicationProtocol.TCP_SOCKET else ESPStructureType.DASK,
            ),
        )

    def put(
        self,
        server_time_measurement: ServerTimeMeasurement,
    ) -> None:
        self._measurements.append(server_time_measurement)
