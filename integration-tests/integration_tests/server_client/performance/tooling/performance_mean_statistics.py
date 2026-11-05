from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import fmean
from typing import ClassVar, Dict, List, Sequence

from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client.performance.tooling.performance_repositories import PerformanceRepositories
from integration_tests.server_client.performance.tooling.performance_repository import PerformanceRepository
from integration_tests.server_client.performance.tooling.performance_result import PerformanceResult


@dataclass(frozen=True)
class PerformanceMeanStatistics:
    # microseconds, like the measured times
    _MEAN_DECIMALS: ClassVar[int] = 6

    _repositories: PerformanceRepositories

    def calculate_and_save_mean_of_actual_since(
        self,
        machine_name: str,
        since: datetime,
        protocol: CommunicationProtocol,
        time_of_calculation: datetime,
        save_path: Path,
    ) -> PerformanceRepository:
        repository = PerformanceRepository.of(save_path)
        for results_of_test in self._grouped_results_by_test_name(self._actual_results(machine_name, since, protocol)).values():
            repository.add(self._mean_of_results(results=results_of_test, date=time_of_calculation))
        return repository

    def _actual_results(self, machine_name: str, since: datetime, protocol: CommunicationProtocol) -> List[PerformanceResult]:
        results: List[PerformanceResult] = []
        for repository in self._repositories.actual_repositories(since=since):
            if repository.machine_name == machine_name and repository.communication_protocol == protocol:
                results.extend(repository.all())
        return results

    @staticmethod
    def _grouped_results_by_test_name(results: Sequence[PerformanceResult]) -> Dict[str, List[PerformanceResult]]:
        grouped: Dict[str, List[PerformanceResult]] = {}
        for result in results:
            grouped.setdefault(result.test_name, []).append(result)
        return grouped

    @classmethod
    def _mean_of_results(cls, results: Sequence[PerformanceResult], date: datetime) -> PerformanceResult:
        if len({(result.test_name, result.communication_protocol, result.machine) for result in results}) != 1:
            raise ValueError("Only results of one test, protocol and machine can be averaged.")
        first = results[0]
        return PerformanceResult(
            test_name=first.test_name,
            start_time_in_seconds=cls._mean_of([result.start_time_in_seconds for result in results]),
            execution_time_in_seconds=cls._mean_of([result.execution_time_in_seconds for result in results]),
            stop_time_in_seconds=cls._mean_of([result.stop_time_in_seconds for result in results]),
            server_uptime_in_seconds=cls._mean_of([result.server_uptime_in_seconds for result in results]),
            total_time_in_seconds=round(fmean(result.total_time_in_seconds for result in results), cls._MEAN_DECIMALS),
            tags=[f"mean_of_{len(results)}_runs"],
            communication_protocol=first.communication_protocol,
            date=date,
            machine=first.machine,
        )

    @classmethod
    def _mean_of(cls, times: Sequence[float | None]) -> float | None:
        measured = [time for time in times if time is not None]
        return round(fmean(measured), cls._MEAN_DECIMALS) if measured else None
