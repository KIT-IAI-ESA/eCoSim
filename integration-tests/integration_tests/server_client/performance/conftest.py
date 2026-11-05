from server_client.performance.tooling.performance_setup import current_machine

from integration_tests.server_client.performance.tooling.performance_repositories import PerformanceRepositories
from integration_tests.server_client.performance.tooling.performance_run_statistics import collected_performance_statistics


def pytest_terminal_summary() -> None:
    """This hook prints all performance statistics and writes them to `actual/DATE_TIME_MACHINE_results.log`."""
    statistics = collected_performance_statistics()
    if statistics:
        statistics.print_summary_to_log_and_file(
            file_path=PerformanceRepositories.create().summary_file_path(machine_name=current_machine()),
        )
