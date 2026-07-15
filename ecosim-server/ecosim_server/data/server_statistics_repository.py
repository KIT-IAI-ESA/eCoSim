from abc import abstractmethod, ABC

from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement


class ServerTimeMeasurementRepository(ABC):
    @abstractmethod
    def put(
        self,
        server_time_measurement: ServerTimeMeasurement,
    ) -> None:
        pass
