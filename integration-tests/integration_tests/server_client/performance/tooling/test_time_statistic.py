import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client.performance.tooling.time_statistic import TimeStatistic


def create_statistic(expected: float | None, current: float | None) -> TimeStatistic:
    return TimeStatistic(
        test_name="test_a",
        communication_protocol=CommunicationProtocol.DASK,
        measurement_name="total_time_in_seconds",
        expected=expected,
        current=current,
    )


@pytest.mark.parametrize(
    ("expected", "current", "deviation"),
    [(2.0, 2.5, 0.25), (2.0, 1.0, -0.5), (None, 1.0, None), (2.0, None, None), (0.0, 1.0, None)],
    ids=["slower", "faster", "no_baseline", "not_measured", "baseline_zero"],
)
def test_the_deviation_is_relative_to_the_expected_time(expected: float | None, current: float | None, deviation: float | None) -> None:
    assert create_statistic(expected, current).deviation == deviation
