from __future__ import annotations

import time
from typing import Callable

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement
from integration_tests.server_client.performance.tooling.performance_setup import current_machine

from integration_tests.server_client.performance.tooling.performance_repositories import PerformanceRepositories


def assert_performance(
    test_name: str,
    run_test: Callable[[], ServerTimeMeasurement],
    communication_protocol: CommunicationProtocol,
    machine_name: str | None = None,
) -> None:
    """
    Runs the test with `run_test`, which returns the time measurement of the test's server, writes the times to the results of
    the current test run and compares them with the latest expected result of the same test, machine and protocol.

    The result is stored under `test_name` and in addition to a global list, which is printed in the end.
    """
    machine_name = machine_name or current_machine()
    repositories = PerformanceRepositories.create()
    start = time.perf_counter()
    server_measurement = run_test()
    total_time = time.perf_counter() - start

    result = repositories.get_repository_for_current_run(communication_protocol, machine_name).write(
        measurement=server_measurement,
        test_name=test_name,
        total_time=total_time,
    )
    repositories.store_and_compare_with_current(result)
