from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

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
            ServerTimeMeasurement._logger.warning(
                f"Start time for {type} is already set -> nothing happens",
            )
            return
        self._start_times[type] = datetime.now()

    def set_end(
        self,
        type: ServerTimeMeasurementType,
    ) -> None:
        if type in self._end_times.keys():
            ServerTimeMeasurement._logger.warning(
                f"End time for {type} is already set -> nothing happens",
            )
            return
        self._end_times[type] = datetime.now()

    def _run_time_hh_mm_ss(
        self,
        type: ServerTimeMeasurementType,
    ) -> str | None:
        if type not in self._start_times.keys():
            ServerTimeMeasurement._logger.warning(
                f"Measurement type {type} as no start time -> cannot calculate runtime",
            )
            return None
        if type not in self._end_times.keys():
            ServerTimeMeasurement._logger.warning(
                f"Measurement type {type} as no end time (start time: {self._start_times[type]}) -> cannot calculate runtime",
            )
            return None
        delta = self._end_times[type] - self._start_times[type]
        total_seconds = delta.total_seconds()
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m {seconds:.3f}s (= {total_seconds:.3f}s total)"

    def print_statistics(self) -> None:
        GlobalLogger.print_values(
            header="SERVER MEASUREMENT",
            value_pairs={
                "Simulation start time": self._run_time_hh_mm_ss(
                    ServerTimeMeasurementType.SIMULATION_START,
                ),
                "Simulation execution time": self._run_time_hh_mm_ss(
                    ServerTimeMeasurementType.SIMULATION_EXECUTION,
                ),
                "Simulation stop time": self._run_time_hh_mm_ss(
                    ServerTimeMeasurementType.SIMULATION_STOP,
                ),
                "Server uptime": self._run_time_hh_mm_ss(
                    ServerTimeMeasurementType.SERVER_UPTIME,
                ),
            },
        )

    def _run_time_in_seconds(
        self,
        type: ServerTimeMeasurementType,
    ) -> int:
        start_time = self._start_times[type]
        end_time = self._end_times[type]
        return int((end_time - start_time).total_seconds())

    def get(
        self,
        type: ServerTimeMeasurementType,
    ) -> "ServerTimeMeasurement.Entry":
        return ServerTimeMeasurement.Entry(
            type=type,
            start_time=self._start_times[type],
            end_time=self._end_times[type],
            run_time_in_seconds=self._run_time_in_seconds(type),
        )

    @dataclass(frozen=True)
    class Entry:
        type: ServerTimeMeasurementType
        start_time: datetime
        end_time: datetime
        run_time_in_seconds: int


class ServerTimeMeasurementType(Enum):
    SIMULATION_START = 0
    SIMULATION_EXECUTION = 1
    SIMULATION_STOP = 2
    SERVER_UPTIME = 3
    RESTORE_SIMULATION_RUN = 3
