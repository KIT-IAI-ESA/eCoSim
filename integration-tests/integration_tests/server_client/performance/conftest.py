from ecosim_common.tech.logger.global_logger import GlobalLogger

from integration_tests.server_client.performance.tooling.performance_run_statistics import collected_performance_statistics
from integration_tests.server_client.performance.tooling.time_statistic import transform_statistics_for_output


def pytest_terminal_summary() -> None:
    """This hook is used to print all performance statistics."""
    statistics = collected_performance_statistics()
    if statistics:
        GlobalLogger.print_values(header="Performance statistics", value_pairs=transform_statistics_for_output(statistics))
