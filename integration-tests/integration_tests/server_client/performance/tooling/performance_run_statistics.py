from __future__ import annotations

from typing import List, Sequence

from integration_tests.server_client.performance.tooling.time_statistic import TimeStatistic

_PERFORMANCE_STATISTICS: List[TimeStatistic] = []


def add_performance_statistics(statistics: Sequence[TimeStatistic]) -> None:
    _PERFORMANCE_STATISTICS.extend(statistics)


def collected_performance_statistics() -> List[TimeStatistic]:
    return list(_PERFORMANCE_STATISTICS)
