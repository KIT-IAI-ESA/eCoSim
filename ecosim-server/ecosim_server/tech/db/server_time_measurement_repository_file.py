from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.tech.db.file_repository import FileRepository


@dataclass(frozen=True)
class ServerTimeMeasurementEntryFileRepository(FileRepository[ServerTimeMeasurement.Entry]):
    @override
    def entry_type(self) -> type[ServerTimeMeasurement.Entry]:
        return ServerTimeMeasurement.Entry


@dataclass(frozen=True)
class ServerTimeMeasurementRepositoryFile(ServerTimeMeasurementRepository):
    """
    Appends every measured phase to the file, so the last entry of a type is the current one.
    """

    _entries: ServerTimeMeasurementEntryFileRepository = field()

    @staticmethod
    def create(
        directory: Path,
        communication_protocol: CommunicationProtocol,
    ) -> ServerTimeMeasurementRepositoryFile:
        return ServerTimeMeasurementRepositoryFile(
            _entries=ServerTimeMeasurementEntryFileRepository(
                _file_path=directory / "server_time_measurement.jsonl",
                _write_lock=ParallelLock.for_protocol(communication_protocol, dask_name="server_time_measurement.jsonl_lock"),
            ),
        )

    @override
    def put(
        self,
        server_time_measurement: ServerTimeMeasurement,
    ) -> None:
        for measurement_type in ServerTimeMeasurementType:
            entry = server_time_measurement.get_or_none(measurement_type)
            if entry is None:  # a phase the run never entered doesn't have anything to persist
                continue
            self._entries.add(entry)

    @override
    def get_start(
        self,
        type: ServerTimeMeasurementType,
    ) -> datetime | None:
        entry = self._latest_entry_of(type)
        return entry.start_time if entry is not None else None

    @override
    def get_end(
        self,
        type: ServerTimeMeasurementType,
    ) -> datetime | None:
        entry = self._latest_entry_of(type)
        return entry.end_time if entry is not None else None

    def file_path(self) -> Path:
        return self._entries.file_path()

    def _latest_entry_of(
        self,
        measurement_type: ServerTimeMeasurementType,
    ) -> ServerTimeMeasurement.Entry | None:
        matching_entries = [entry for entry in self._entries.all() if entry.type is measurement_type]
        if not matching_entries:
            self._logger.warning("Measurement type %s is not in %s", measurement_type, self.file_path())
            return None
        return matching_entries[-1]
