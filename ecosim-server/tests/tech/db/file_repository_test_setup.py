from __future__ import annotations

import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, override

from ecosim_common.tech.parallel.parallel_lock import NullLock, ParallelLock
from ecosim_server.tech.db.file_repository import FileRepository

TIMESTAMP = datetime.datetime(2026, 8, 26, 10, 0, 0, tzinfo=datetime.timezone.utc)


@dataclass(frozen=True)
class Reading:
    name: str
    value: float


@dataclass
class Measurement:
    timestamp: datetime.datetime
    readings: Tuple[Reading, ...]


@dataclass(frozen=True)
class MeasurementFileRepository(FileRepository[Measurement]):
    @override
    def entry_type(self) -> type[Measurement]:
        return Measurement


class RecordingLock(NullLock):
    """Counts how often the lock is entered."""

    def __init__(self) -> None:
        self.enter_count = 0

    @override
    def __enter__(self) -> RecordingLock:
        self.enter_count += 1
        return self


def create_measurement(minute: int = 0) -> Measurement:
    return Measurement(
        timestamp=TIMESTAMP + datetime.timedelta(minutes=minute),
        readings=(Reading(name="room_temperature", value=293.15 + minute),),
    )


def create_repository(
    file_path: Path,
    write_lock: ParallelLock | None = None,
) -> MeasurementFileRepository:
    return MeasurementFileRepository(
        _file_path=file_path,
        _write_lock=write_lock or NullLock(),
    )


def read_lines_of(file_path: Path) -> List[str]:
    return file_path.read_text(encoding="utf-8").splitlines()
