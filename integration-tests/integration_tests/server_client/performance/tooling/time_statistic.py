from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence

from ecosim_common.communication.communication_protocol import CommunicationProtocol


@dataclass(frozen=True)
class TimeStatistic:
    """One compared time of a performance test run: the `expected` time of the current results and the `current` time of this run."""

    test_name: str
    communication_protocol: CommunicationProtocol
    measurement_name: str
    expected: float | None
    current: float | None

    @property
    def deviation(self) -> float | None:
        """`0.25` is 25% slower, `-0.5` is 50% faster; None if there is nothing to compare."""
        if self.expected is None or self.current is None or self.expected == 0:
            return None
        return (self.current - self.expected) / self.expected

    def is_slower_than(self, tolerance: float) -> bool:
        return self.deviation is not None and self.deviation > tolerance

    def describe(self) -> str:
        deviation = "-" if self.deviation is None else f"{self.deviation:+.1%}"
        return (
            f"{self.measurement_name}: "
            f"expected {TimeStatistic._format_second_to_string(self.expected)} | "
            f"current {TimeStatistic._format_second_to_string(self.current)} | "
            f"deviation {deviation}"
        )

    @staticmethod
    def _format_second_to_string(
        time: float | None,
    ) -> str:
        return "-" if time is None else f"{time:.3f}s"


def transform_statistics_for_output(statistics: Sequence[TimeStatistic]) -> Dict[str, List[str]]:
    """The statistics grouped by test and protocol, as the value pairs of `GlobalLogger.print_values`."""
    values: Dict[str, List[str]] = {}
    for statistic in statistics:
        values.setdefault(f"{statistic.test_name} ({statistic.communication_protocol.serialized})", []).append(statistic.describe())
    return values
