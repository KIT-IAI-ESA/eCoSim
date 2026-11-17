import pytest
from ecosim_common.communication.message_type import MessageType
from ecosim_server.progress_logger import progress_logger
from ecosim_test_common.test_data.manual_clock import ManualClock
from tests.simulation.simulation_executor_test_setup import answer_after_advancing, error_of_bounded_run, executor_with_client


def test_the_progress_lines_of_a_run_are_logged_by_the_progress_logger(caplog: pytest.LogCaptureFixture) -> None:
    clock = ManualClock()
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_STEP: answer_after_advancing(clock=clock, seconds=10)}, clock=clock)

    assert error_of_bounded_run(executor) is None

    (line,) = [record.getMessage() for record in caplog.records if record.name == progress_logger.name]
    assert line.startswith("Step 1 of 2 ")


@pytest.mark.parametrize(("restore", "restored_steps"), [(False, 0), (True, 1)])
def test_the_summary_of_a_run_counts_the_restored_steps_apart(restore: bool, restored_steps: int) -> None:
    executor, _ = executor_with_client(reactions={}, restore=restore)

    assert error_of_bounded_run(executor) is None

    summary = executor.run_summary(failure_reason=None)
    assert (summary.completed_steps, summary.restored_steps) == (2, restored_steps)
