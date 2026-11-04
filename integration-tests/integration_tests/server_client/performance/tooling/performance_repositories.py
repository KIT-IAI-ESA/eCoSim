from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from integration_tests.server_client.performance.tooling.performance_repository import PerformanceRepository
from integration_tests.server_client.performance.tooling.performance_result_setup import current_machine

import integration_tests


@dataclass(frozen=True)
class PerformanceRepositories:
    """
    One `PerformanceRepository` per `*.jsonl` file.

    `current` holds the files directly in the performance folder (subfolders are not read),
    `history` the files the test runs wrote to its `history` subfolder.

    Since all logic runs in the same pytest process, threading locks/structures are enough, and we don't need to consider dask.
    """

    _DATA_FOLDER: ClassVar[Path] = Path(integration_tests.__file__).parent / "resources" / "performance"
    _HISTORY_FOLDER: ClassVar[Path] = _DATA_FOLDER / "history"
    _DATETIME_OF_TEST_RUN: ClassVar[datetime] = datetime.now()

    _current_repositories: ESPMap[Path, PerformanceRepository]
    _history_repositories: ESPMap[Path, PerformanceRepository]

    @staticmethod
    def create(data_folder: Path | None = None) -> PerformanceRepositories:
        data_folder = data_folder or PerformanceRepositories._DATA_FOLDER
        return PerformanceRepositories(
            _current_repositories=PerformanceRepositories._repositories_of_folder(data_folder),
            _history_repositories=PerformanceRepositories._repositories_of_folder(data_folder / "history"),
        )

    def get_current_for(
        self,
        communication_protocol: CommunicationProtocol,
        machine_name: str | None = None,
    ) -> PerformanceRepository | None:
        result: PerformanceRepository | None = None
        for repository in self._current_repositories.values():
            if repository.communication_protocol == communication_protocol and repository.machine_name == machine_name:
                if result is None:
                    result = repository
                else:
                    result = result if result.date_of_test_run >= repository.date_of_test_run else repository
        return result

    def get_repository_for_current_run(
        self,
        communication_protocol: CommunicationProtocol,
    ) -> PerformanceRepository:
        path = self._get_path_for_repository_for_current_run(communication_protocol)
        with self._history_repositories.transaction() as history_repositories:
            if path not in history_repositories.keys():
                history_repositories[path] = PerformanceRepository.of(path)
        return self._history_repositories[path]

    @staticmethod
    def _get_path_for_repository_for_current_run(
        communication_protocol: CommunicationProtocol,
    ) -> Path:
        datetime_string = PerformanceRepositories._DATETIME_OF_TEST_RUN.strftime(PerformanceRepository.FILE_NAME_DATE_TIME_FORMAT)
        file_name = f"{datetime_string}_{communication_protocol.serialized}_{current_machine()}.jsonl"
        return PerformanceRepositories._HISTORY_FOLDER / file_name

    @staticmethod
    def _repositories_of_folder(folder: Path) -> ESPMap[Path, PerformanceRepository]:
        files = sorted(folder.glob("*.jsonl")) if folder.is_dir() else []
        return ESPMap.of_type(
            map_type=ESPStructureType.THREAD,
            data={file: PerformanceRepository.of(file) for file in files},
        )
