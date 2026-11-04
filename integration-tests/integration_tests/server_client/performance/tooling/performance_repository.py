from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Tuple, override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.tech.db.file_repository import FileRepository
from integration_tests.server_client.performance.tooling.performance_result import PerformanceResult


@dataclass(frozen=True)
class PerformanceRepository(FileRepository[PerformanceResult]):
    FILE_NAME_DATE_TIME_FORMAT: ClassVar[str] = "%Y-%m-%d_%H%M%S"

    communication_protocol: CommunicationProtocol
    date_of_test_run: datetime
    machine_name: str

    @override
    def entry_type(self) -> type[PerformanceResult]:
        return PerformanceResult

    @staticmethod
    def of(file_path: Path) -> PerformanceRepository:
        return PerformanceRepository(
            _file_path=file_path,
            # the ecosim servers of the integration tests run in the pytest process, so a thread lock is enough
            _write_lock=ParallelLock.thread(),
            communication_protocol=PerformanceRepository._extract_communication_protocol(file_path),
            date_of_test_run=PerformanceRepository._extract_date_of_test_run(file_path),
            machine_name=PerformanceRepository._extract_machine_name(file_path),
        )

    @staticmethod
    def _extract_communication_protocol(file_path: Path) -> CommunicationProtocol:
        return CommunicationProtocol.of(PerformanceRepository._file_name_parts(file_path)[2])

    @staticmethod
    def _extract_date_of_test_run(file_path: Path) -> datetime:
        date, time, _, _ = PerformanceRepository._file_name_parts(file_path)
        return datetime.strptime(f"{date}_{time}", PerformanceRepository.FILE_NAME_DATE_TIME_FORMAT)

    @staticmethod
    def _extract_machine_name(file_path: Path) -> str:
        _, _, _, machine_name = PerformanceRepository._file_name_parts(file_path)
        return machine_name

    @staticmethod
    def _file_name_parts(file_path: Path) -> Tuple[str, str, str, str]:
        """
        `DATE_TIME_PROTOCOL_MACHINE` -> (DATE, TIME, PROTOCOL, MACHINE);
        PROTOCOL and MACHINE can contain '_' so a little bit work extra work is needed to correctly extract the protocol.
        """
        parts = file_path.stem.split("_", 2)
        if len(parts) == 3:
            date, time, protocol_and_machine = parts
            for protocol in CommunicationProtocol:
                if protocol_and_machine.startswith(f"{protocol.serialized}_"):
                    return date, time, protocol.serialized, protocol_and_machine.removeprefix(f"{protocol.serialized}_")
        raise ValueError(f"The file name '{file_path.name}' is not in the format DATE_TIME_PROTOCOL_MACHINE.jsonl.")

    def write(
        self,
        measurement: ServerTimeMeasurement,
        test_name: str,
        total_time: float,
    ) -> None:
        entry = self._create_result(
            measurement=measurement,
            test_name=test_name,
            total_time=total_time,
        )
        self.add(entry)

    def _create_result(
        self,
        measurement: ServerTimeMeasurement,
        test_name: str,
        total_time: float,
    ) -> PerformanceResult:
        return PerformanceResult(
            test_name=test_name,
            start_time_in_seconds=measurement.get_runtime_in_seconds(ServerTimeMeasurementType.SIMULATION_START),
            execution_time_in_seconds=measurement.get_runtime_in_seconds(ServerTimeMeasurementType.SIMULATION_EXECUTION),
            stop_time_in_seconds=measurement.get_runtime_in_seconds(ServerTimeMeasurementType.SIMULATION_STOP),
            server_uptime_in_seconds=measurement.get_runtime_in_seconds(ServerTimeMeasurementType.SERVER_UPTIME),
            total_time_in_seconds=total_time,
            tags=[],
            communication_protocol=self.communication_protocol,
            date=datetime.now(),
            machine=self.machine_name,
        )
