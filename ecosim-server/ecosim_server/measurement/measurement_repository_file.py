from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_server.tech.db.file_repository import FileRepository


@dataclass(frozen=True)
class MeasurementEntryFileRepository(FileRepository[MeasurementEntry]):
    @override
    def entry_type(self) -> type[MeasurementEntry]:
        return MeasurementEntry


@dataclass(frozen=True)
class MeasurementRepositoryFile(MeasurementRepository):
    """Stores the measurements of one simulator in its own file, like the database stores them in their own table."""

    _entries: MeasurementEntryFileRepository = field()

    @staticmethod
    def create(
        directory: Path,
        simulator_name: str,
        communication_protocol: CommunicationProtocol,
    ) -> MeasurementRepositoryFile:
        return MeasurementRepositoryFile(
            _entries=MeasurementEntryFileRepository(
                _file_path=directory / f"module_{simulator_name}.jsonl",
                _write_lock=ParallelLock.for_protocol(communication_protocol, dask_name=f"file_repo_lock_{simulator_name}"),
            ),
        )

    @override
    def add(
        self,
        values: Tuple[ProtocolInterfaceValue, ...],
        timestamp: datetime.datetime,
    ) -> None:
        self._entries.add(
            MeasurementEntry(
                values=values,
                timestamp=timestamp,
            ),
        )

    @override
    def all(self) -> List[MeasurementEntry]:
        return self._entries.all()

    @override
    def remove_starting_at(self, timestamp: datetime.datetime) -> None:
        self._entries.remove_where(condition=lambda entry: entry.timestamp >= timestamp)

    def file_path(self) -> Path:
        return self._entries.file_path()
