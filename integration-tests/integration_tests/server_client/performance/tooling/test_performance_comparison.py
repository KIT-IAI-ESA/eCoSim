import pytest
from server_client.performance.tooling.performance_setup import GITHUB_CI_MACHINE, primary_tolerance_for

ALL_TIMES = ["start_time_in_seconds", "execution_time_in_seconds", "stop_time_in_seconds", "server_uptime_in_seconds", "total_time_in_seconds"]


@pytest.mark.parametrize(("machine_name", "tolerance"), [(GITHUB_CI_MACHINE, 0.15), ("local_my_laptop", 0.10)])
def test_the_ci_tolerates_a_bigger_deviation_than_a_local_machine(machine_name: str, tolerance: float) -> None:
    assert primary_tolerance_for(machine_name) == tolerance
