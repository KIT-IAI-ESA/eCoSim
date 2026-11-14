import pytest
from ecosim_common.communication.message_type import MessageType
from ecosim_test_common.test_data.manual_clock import ManualClock
from tests.simulation.simulation_executor_test_setup import answer_after_advancing, error_of_bounded_run, executor_with_client


def test_the_progress_lines_of_a_run_are_logged_under_the_name_progress(caplog: pytest.LogCaptureFixture) -> None:
    clock = ManualClock()
    executor, _ = executor_with_client(reactions={MessageType.SIMULATION_STEP: answer_after_advancing(clock=clock, seconds=10)}, clock=clock)

    assert error_of_bounded_run(executor) is None

    assert [record.getMessage() for record in caplog.records if record.name == "Progress"] == [
        "Step 1 of 2 (50 %), simulated 2025-01-01 00:00:01, 10 s per step, about 10 s left",
    ]
