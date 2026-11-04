from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar, List

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from server_client.performance.tooling.performance_result import PerformanceResult
from server_client.performance.tooling.performance_run_statistics import add_performance_statistics
from server_client.performance.tooling.performance_setup import current_machine, slower_times, tolerance_for
from server_client.performance.tooling.time_statistic import TimeStatistic, transform_statistics_for_output

import integration_tests
from integration_tests.server_client.performance.tooling.performance_repository import PerformanceRepository


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
        machine_name: str | None = None,
    ) -> PerformanceRepository:
        path = self._get_path_for_repository_for_current_run(communication_protocol, machine_name or current_machine())
        with self._history_repositories.transaction() as history_repositories:
            if path not in history_repositories.keys():
                history_repositories[path] = PerformanceRepository.of(path)
        return self._history_repositories[path]

    @staticmethod
    def _get_path_for_repository_for_current_run(
        communication_protocol: CommunicationProtocol,
        machine_name: str,
    ) -> Path:
        datetime_string = PerformanceRepositories._DATETIME_OF_TEST_RUN.strftime(PerformanceRepository.FILE_NAME_DATE_TIME_FORMAT)
        file_name = f"{datetime_string}_{communication_protocol.serialized}_{machine_name}.jsonl"
        return PerformanceRepositories._HISTORY_FOLDER / file_name

    @staticmethod
    def _repositories_of_folder(folder: Path) -> ESPMap[Path, PerformanceRepository]:
        files = sorted(folder.glob("*.jsonl")) if folder.is_dir() else []
        return ESPMap.of_type(
            map_type=ESPStructureType.THREAD,
            data={file: PerformanceRepository.of(file) for file in files},
        )

    def store_and_compare_with_current(
        self,
        result: PerformanceResult,
    ) -> None:
        current_repository = self.get_current_for(result.communication_protocol, result.machine)
        baseline = current_repository.latest_of(result.test_name) if current_repository else None
        statistics = result.compare_to(baseline)
        self._add_to_logs_and_global_statistic(result, statistics)
        if baseline is None:
            message = (
                f"No current result of '{result.test_name}' for machine '{result.machine}' and protocol '{result.communication_protocol.serialized}'."
            )
            pytest.fail(message)
        tolerance = tolerance_for(result.machine)
        deviations = [statistic.describe() for statistic in slower_times(statistics, tolerance)]
        if deviations:
            pytest.fail(f"'{result.test_name}' ({result.communication_protocol.serialized}) is slower than {tolerance:.0%}: " + "; ".join(deviations))

    @staticmethod
    def _add_to_logs_and_global_statistic(result: PerformanceResult, statistics: List[TimeStatistic]) -> None:
        GlobalLogger.print_values(header=f"Performance of '{result.test_name}'", value_pairs=transform_statistics_for_output(statistics))
        add_performance_statistics(statistics)
