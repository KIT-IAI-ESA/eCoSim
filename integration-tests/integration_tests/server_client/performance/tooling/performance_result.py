from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from server_client.performance.tooling.performance_setup import primary_tolerance_for, secondary_tolerance_for
from server_client.performance.tooling.time_statistic import TimeStatistic


@dataclass(frozen=True)
class PerformanceResult:
    test_name: str
    start_time_in_seconds: float | None
    execution_time_in_seconds: float | None
    stop_time_in_seconds: float | None
    server_uptime_in_seconds: float | None
    total_time_in_seconds: float
    tags: List[str]
    communication_protocol: CommunicationProtocol
    date: datetime
    machine: str

    def compare_to(
        self,
        baseline: PerformanceResult | None,
    ) -> List[TimeStatistic]:
        """
        The compared times of `self` next to the ones of the `baseline` (expected is None without a baseline).

        `server_uptime_in_seconds` is skipped, because total_time is more meaningful.
        """
        primary_tolerance = primary_tolerance_for(self.machine)
        secondary_tolerance = secondary_tolerance_for(self.machine)
        return [
            TimeStatistic(
                test_name=self.test_name,
                communication_protocol=self.communication_protocol,
                measurement_name="start_time_in_seconds",
                expected=baseline.start_time_in_seconds if baseline else None,
                current=self.start_time_in_seconds,
                tolerance=secondary_tolerance,
            ),
            TimeStatistic(
                test_name=self.test_name,
                communication_protocol=self.communication_protocol,
                measurement_name="execution_time_in_seconds",
                expected=baseline.execution_time_in_seconds if baseline else None,
                current=self.execution_time_in_seconds,
                tolerance=primary_tolerance,
            ),
            TimeStatistic(
                test_name=self.test_name,
                communication_protocol=self.communication_protocol,
                measurement_name="stop_time_in_seconds",
                expected=baseline.stop_time_in_seconds if baseline else None,
                current=self.stop_time_in_seconds,
                tolerance=secondary_tolerance,
            ),
            TimeStatistic(
                test_name=self.test_name,
                communication_protocol=self.communication_protocol,
                measurement_name="total_time_in_seconds",
                expected=baseline.total_time_in_seconds if baseline else None,
                current=self.total_time_in_seconds,
                tolerance=secondary_tolerance,
            ),
        ]
