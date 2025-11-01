from dataclasses import dataclass, field
from typing import List

from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement


@dataclass(frozen=True)
class ServerTimeMeasurementRepositoryInMemory(ServerTimeMeasurementRepository):
    _measurements: List[ServerTimeMeasurement] = field(default_factory=list)

    def put(
        self,
        server_time_measurement: ServerTimeMeasurement,
    ):
        self._measurements.append(server_time_measurement)
