from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import ClassVar

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType

from integration_tests.server_client.performance.tooling.performance_repository import PerformanceRepository
from integration_tests.server_client.performance.tooling.performance_result import PerformanceResult
from integration_tests.server_client.performance.tooling.performance_run_statistics import add_performance_statistics
from integration_tests.server_client.performance.tooling.performance_setup import (
    FILE_NAME_DATE_TIME_FORMAT,
    fallback_machine_name_for_local_repository,
    is_local_machine,
)
from integration_tests.server_client.performance.tooling.performance_statistics import PerformanceStatistics
from integration_tests.tech.integration_test_resource_utils import performance_data_resource_path


@dataclass(frozen=True)
class PerformanceRepositories:
    """
    One `PerformanceRepository` per `*.jsonl` file.

    `expected` holds the files directly in the performance folder (subfolders are not read),
    `actual` the files the test runs wrote to its `actual` subfolder.

    Since all logic runs in the same pytest process, threading locks/structures are enough, and we don't need to consider dask.

    Local machines always start with `local_`. If the current local machine does not have any data for comparison, it uses the data
    of `DEFAULT_MACHINE_NAME_FOR_FALLBACK_LOCAL_REPOSITORY`.
    """

    ACTUAL_FOLDER_NAME: ClassVar[str] = "actual"
    DATETIME_OF_TEST_RUN: ClassVar[datetime] = datetime.now()
    _DEFAULT_EXPECTED_FOLDER: ClassVar[Path] = performance_data_resource_path()

    _expected_repositories: ESPMap[Path, PerformanceRepository]
    _actual_repositories: ESPMap[Path, PerformanceRepository]
    _expected_folder: Path
    _actual_folder: Path

    @classmethod
    def create(cls, data_folder: Path | None = None) -> PerformanceRepositories:
        expected_folder = data_folder or cls._DEFAULT_EXPECTED_FOLDER
        actual_folder = expected_folder / cls.ACTUAL_FOLDER_NAME
        return PerformanceRepositories(
            _expected_repositories=cls._repositories_of_folder(expected_folder),
            _actual_repositories=cls._repositories_of_folder(actual_folder),
            _expected_folder=expected_folder,
            _actual_folder=actual_folder,
        )

    def get_expected_for(
        self,
        communication_protocol: CommunicationProtocol,
        machine_name: str,
    ) -> PerformanceRepository | None:
        """Local machines have a fallback - all others not."""
        result: PerformanceRepository | None = None
        fallback_machine_name = fallback_machine_name_for_local_repository()
        fallback: PerformanceRepository | None = None
        for repository in self._expected_repositories.values():
            if repository.communication_protocol == communication_protocol and repository.machine_name == machine_name:
                result = repository if (result is None or result.date_of_test_run < repository.date_of_test_run) else result
            if (
                is_local_machine(machine_name)
                and repository.communication_protocol == communication_protocol
                and repository.machine_name == fallback_machine_name
            ):
                fallback = repository if (fallback is None or fallback.date_of_test_run < repository.date_of_test_run) else fallback
        return result or fallback

    def get_repository_for_current_run(
        self,
        communication_protocol: CommunicationProtocol,
        machine_name: str,
    ) -> PerformanceRepository:
        path = self._get_path_for_repository_for_current_run(communication_protocol, machine_name)
        with self._actual_repositories.transaction() as history_repositories:
            if path not in history_repositories.keys():
                history_repositories[path] = PerformanceRepository.of(path)
        return self._actual_repositories[path]

    def _get_path_for_repository_for_current_run(
        self,
        communication_protocol: CommunicationProtocol,
        machine_name: str,
    ) -> Path:
        return self._actual_folder / (
            f"{self.DATETIME_OF_TEST_RUN.strftime(FILE_NAME_DATE_TIME_FORMAT)}_{communication_protocol.serialized}_{machine_name}.jsonl"
        )

    def summary_file_path(self, machine_name: str) -> Path:
        return self._actual_folder / (f"{self.DATETIME_OF_TEST_RUN.strftime(FILE_NAME_DATE_TIME_FORMAT)}_{machine_name}_results.log")

    @classmethod
    def _repositories_of_folder(cls, folder: Path) -> ESPMap[Path, PerformanceRepository]:
        files = sorted(folder.glob("*.jsonl")) if folder.is_dir() else []
        return ESPMap.of_type(
            map_type=ESPStructureType.THREAD,
            data={file: PerformanceRepository.of(file) for file in files},
        )

    def store_and_compare_with_current(
        self,
        result: PerformanceResult,
    ) -> None:
        current_repository = self.get_expected_for(result.communication_protocol, result.machine)
        baseline = current_repository.latest_of(result.test_name) if current_repository else None
        statistics = result.compare_to(baseline)
        self._add_to_logs_and_global_statistic(result, statistics)
        if baseline is None:
            message = (
                f"No current result of '{result.test_name}' for machine '{result.machine}' and protocol '{result.communication_protocol.serialized}'."
            )
            pytest.fail(message)
        too_slow = statistics.filter_slower_than_expected()
        if too_slow:
            pytest.fail(f"'{result.test_name}' ({result.communication_protocol.serialized}) is slower than tolerance: {too_slow.describe()}")

    @staticmethod
    def _add_to_logs_and_global_statistic(result: PerformanceResult, statistics: PerformanceStatistics) -> None:
        GlobalLogger.logger.info("Performance of '%s' (%s)", result.test_name, result.communication_protocol.serialized)
        for line in statistics.as_table():
            GlobalLogger.logger.info("%s", line)
        add_performance_statistics(statistics)
