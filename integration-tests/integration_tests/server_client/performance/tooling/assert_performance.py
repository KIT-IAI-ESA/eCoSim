from __future__ import annotations

import time
from typing import Callable, TypeVar

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement
from server_client.performance.tooling.performance_setup import current_machine

from integration_tests.server_client.performance.tooling.performance_repositories import PerformanceRepositories

T = TypeVar("T")


def assert_performance(
    test: Callable[[T], None],
    test_argument: T,
    server_measurement: ServerTimeMeasurement,
    communication_protocol: CommunicationProtocol,
    machine_name: str | None = None,
) -> None:
    """
    Runs `test(test_argument)`, writes its times to the history of the current test run and compares them with
    the latest current result of the same test, machine and protocol.

    The result is stored under the `__name__` of `test` and in addition to a global list, which is printed in the end.
    """
    machine_name = machine_name or current_machine()
    repositories = PerformanceRepositories.create()
    start = time.perf_counter()
    test(test_argument)
    total_time = time.perf_counter() - start

    result = repositories.get_repository_for_current_run(communication_protocol, machine_name).write(
        measurement=server_measurement,
        test_name=test.__name__,
        total_time=total_time,
    )
    repositories.store_and_compare_with_current(result)
