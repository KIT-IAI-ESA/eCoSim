from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client.performance.tooling.performance_statistics import PerformanceStatistics
from integration_tests.server_client.performance.tooling.time_statistic import TimeStatistic


def create_statistic(
    measurement_name: str,
    expected: float | None,
    current: float | None,
    test_name: str = "test_a",
) -> TimeStatistic:
    return TimeStatistic(
        test_name=test_name,
        communication_protocol=CommunicationProtocol.DASK,
        measurement_name=measurement_name,
        expected=expected,
        current=current,
        tolerance=0.2,
    )


def test_only_the_statistics_slower_than_their_tolerance_are_slower_than_expected() -> None:
    too_slow = create_statistic("too_slow", expected=2.0, current=2.5)
    within_tolerance = create_statistic("within_tolerance", expected=2.0, current=2.2)
    no_baseline = create_statistic("no_baseline", expected=None, current=9.0)

    statistics = PerformanceStatistics.of([too_slow, within_tolerance, no_baseline])

    assert list(statistics.filter_slower_than_expected()) == [too_slow]


def test_statistics_can_be_combined() -> None:
    first = create_statistic("first", expected=1.0, current=1.0)
    second = create_statistic("second", expected=1.0, current=1.0)
    assert list(PerformanceStatistics.of([first]) + PerformanceStatistics.of([second])) == [first, second]


def test_empty_and_none_empty_behave_like_lists() -> None:
    assert not PerformanceStatistics.of([])
    assert PerformanceStatistics.of([create_statistic("total", 1.0, 1.0)])
