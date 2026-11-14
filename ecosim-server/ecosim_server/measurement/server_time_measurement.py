from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType


class ServerTimeMeasurement:
    _logger = ESPLogger("ServerMeasurement")

    def __init__(
        self,
        protocol: CommunicationProtocol,
    ) -> None:
        self._start_times: ESPMap[ServerTimeMeasurementType, datetime] = ESPMap.of_type(
            map_type=ESPStructureType.THREAD if protocol == CommunicationProtocol.TCP_SOCKET else ESPStructureType.DASK_VARIABLE,
            dask_name="server_measurements_start_time",
        )
        self._end_times: ESPMap[ServerTimeMeasurementType, datetime] = ESPMap.of_type(
            map_type=ESPStructureType.THREAD if protocol == CommunicationProtocol.TCP_SOCKET else ESPStructureType.DASK_VARIABLE,
            dask_name="server_measurements_end_time",
        )

    def set_start(
        self,
        type: ServerTimeMeasurementType,
    ) -> None:
        if type in self._start_times.keys():
            ServerTimeMeasurement._logger.warning("Start time for %s is already set -> nothing happens", type)
            return
        self._start_times[type] = datetime.now()

    def set_end(
        self,
        type: ServerTimeMeasurementType,
    ) -> None:
        if type in self._end_times.keys():
            ServerTimeMeasurement._logger.warning("End time for %s is already set -> nothing happens", type)
            return
        self._end_times[type] = datetime.now()

    def _run_time_hh_mm_ss(
        self,
        type: ServerTimeMeasurementType,
    ) -> str | None:
        if type not in self._start_times.keys():
            ServerTimeMeasurement._logger.warning("Measurement type %s has no start time -> cannot calculate runtime", type)
            return None
        if type not in self._end_times.keys():
            ServerTimeMeasurement._logger.warning(
                "Measurement type %s as no end time (start time: %s) -> cannot calculate runtime",
                type,
                self._start_times[type],
            )
            return None
        delta = self._end_times[type] - self._start_times[type]
        total_seconds = delta.total_seconds()
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {seconds:.3f}s (= {total_seconds:.3f}s total)"

    def print_statistics(self) -> None:
        GlobalLogger.print_values(header="SERVER MEASUREMENT", value_pairs=self.statistics_values())

    def statistics_values(self) -> dict[str, str | None]:
        labels = {
            ServerTimeMeasurementType.SIMULATION_START: "Simulation start time",
            ServerTimeMeasurementType.RESTORE_SIMULATION_RUN: "Restore time",
            ServerTimeMeasurementType.SIMULATION_EXECUTION: "Simulation execution time",
            ServerTimeMeasurementType.SIMULATION_STOP: "Simulation stop time",
            ServerTimeMeasurementType.SERVER_UPTIME: "Server uptime",
        }
        # a restored run has a restore time instead of a start time
        return {label: self._run_time_hh_mm_ss(measurement_type) for measurement_type, label in labels.items() if self.was_measured(measurement_type)}

    def _run_time_in_seconds(
        self,
        type: ServerTimeMeasurementType,
    ) -> float:
        start_time = self._start_times[type]
        end_time = self._end_times[type]
        return (end_time - start_time).total_seconds()

    def was_measured(
        self,
        type: ServerTimeMeasurementType,
    ) -> bool:
        return type in self._start_times.keys() and type in self._end_times.keys()

    def get_or_none(
        self,
        type: ServerTimeMeasurementType,
    ) -> ServerTimeMeasurement.Entry | None:
        if not self.was_measured(type):
            return None
        return ServerTimeMeasurement.Entry(
            type=type,
            start_time=self._start_times[type],
            end_time=self._end_times[type],
            run_time_in_seconds=self._run_time_in_seconds(type),
        )

    def get_runtime_in_seconds(
        self,
        type: ServerTimeMeasurementType,
    ) -> float | None:
        measurement = self.get_or_none(type)
        if measurement is None:
            return None
        return measurement.run_time_in_seconds

    @dataclass(frozen=True)
    class Entry:
        type: ServerTimeMeasurementType
        start_time: datetime
        end_time: datetime
        run_time_in_seconds: float


@unique
class ServerTimeMeasurementType(Enum):
    SIMULATION_START = 0
    SIMULATION_EXECUTION = 1
    SIMULATION_STOP = 2
    SERVER_UPTIME = 3
    RESTORE_SIMULATION_RUN = 4
