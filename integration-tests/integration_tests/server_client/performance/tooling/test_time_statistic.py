import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client.performance.tooling.performance_setup import MINIMUM_DIFFERENCE_IN_SECONDS
from integration_tests.server_client.performance.tooling.time_statistic import TimeStatistic


def create_statistic(expected: float | None, current: float | None) -> TimeStatistic:
    return TimeStatistic(
        test_name="test_a",
        communication_protocol=CommunicationProtocol.DASK,
        measurement_name="total_time_in_seconds",
        expected=expected,
        current=current,
        tolerance=0.2,
    )


@pytest.mark.parametrize(
    ("expected", "current", "deviation"),
    [(2.0, 2.5, 0.25), (2.0, 1.0, -0.5), (None, 1.0, None), (2.0, None, None), (0.0, 1.0, None)],
    ids=["slower", "faster", "no_baseline", "not_measured", "baseline_zero"],
)
def test_the_deviation_is_relative_to_the_expected_time(expected: float | None, current: float | None, deviation: float | None) -> None:
    assert create_statistic(expected, current).deviation == deviation


def test_a_time_beyond_its_tolerance_is_not_too_slow_within_the_minimum_difference() -> None:
    expected = MINIMUM_DIFFERENCE_IN_SECONDS * 2
    statistic = create_statistic(expected=expected, current=expected + MINIMUM_DIFFERENCE_IN_SECONDS / 2)

    assert not statistic.is_too_slow()
