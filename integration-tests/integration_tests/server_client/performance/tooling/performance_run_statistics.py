from __future__ import annotations

from typing import List

from integration_tests.server_client.performance.tooling.performance_statistics import PerformanceStatistics
from integration_tests.server_client.performance.tooling.time_statistic import TimeStatistic

_PERFORMANCE_STATISTICS: List[TimeStatistic] = []


def add_performance_statistics(statistics: PerformanceStatistics) -> None:
    _PERFORMANCE_STATISTICS.extend(statistics)


def collected_performance_statistics() -> PerformanceStatistics:
    return PerformanceStatistics.of(_PERFORMANCE_STATISTICS)
