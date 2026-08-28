from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Generic, List, TypeVar

from ecosim_common.tech.json.dataclass_json_converter import DataclassInstance, DataclassJsonConverter
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_lock import ParallelLock

GenericEntry = TypeVar("GenericEntry", bound=DataclassInstance)


@dataclass(frozen=True)
class FileRepository(ABC, Generic[GenericEntry]):
    """Append-only repository that stores dataclass entries as JSON lines. NOTE: the dataclass must be serializable by `DataclassJsonConverter`.

    The repository uses the `jsonl` standard (https://jsonl.co/guide/what-is-jsonl).

    Reading is locked because an unlocked read could otherwise pick up a line only written partly.
    """

    _logger: ClassVar[ESPLogger] = ESPLogger("FileRepository")

    _file_path: Path = field()
    _write_lock: ParallelLock = field()

    def __post_init__(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def entry_type(self) -> type[GenericEntry]:
        """The dataclass type that is stored by this repository. It is needed for deserialization."""

    def add(
        self,
        entry: GenericEntry,
    ) -> None:
        with self._write_lock:
            with self._file_path.open("a", encoding="utf-8") as file:
                file.write(f"{DataclassJsonConverter.to_json_string(entry)}\n")

    def all(self) -> List[GenericEntry]:
        with self._write_lock:
            return [self._entry_of_line(line) for line in self._read_lines()]

    def file_path(self) -> Path:
        return self._file_path

    def _read_lines(self) -> List[str]:
        if not self._file_path.exists():
            FileRepository._logger.debug("File %s does not exist yet -> no entries.", self._file_path)
            return []
        with self._file_path.open("r", encoding="utf-8") as file:
            return [line for line in file if line.strip()]

    def _entry_of_line(
        self,
        line: str,
    ) -> GenericEntry:
        return DataclassJsonConverter.of_json_string(self.entry_type(), line)
