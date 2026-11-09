from __future__ import annotations

from dataclasses import dataclass

from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client.performance.tooling.performance_setup import MINIMUM_DIFFERENCE_IN_SECONDS, format_seconds


@dataclass(frozen=True)
class TimeStatistic:
    """One compared time of a performance test run: the `expected` time of the current results and the `current` time of this run."""

    test_name: str
    communication_protocol: CommunicationProtocol
    measurement_name: str
    expected: float | None
    current: float | None
    tolerance: float

    @property
    def deviation(self) -> float | None:
        """`0.25` is 25% slower, `-0.5` is 50% faster; None if there is nothing to compare."""
        if self.expected is None or self.current is None or self.expected == 0:
            return None
        return (self.current - self.expected) / self.expected

    def is_too_slow(self) -> bool:
        if self.deviation is None or self.expected is None or self.current is None:
            return False
        return self.deviation > self.tolerance and self.current - self.expected > MINIMUM_DIFFERENCE_IN_SECONDS

    def describe(self) -> str:
        deviation = "-" if self.deviation is None else f"{self.deviation:+.1%}"
        return f"{self.measurement_name}: expected {format_seconds(self.expected)} | current {format_seconds(self.current)} | deviation {deviation}"

    def describe_with_result(self) -> str:
        return f"!FAILED! {self.describe()}" if self.is_too_slow() else self.describe()
