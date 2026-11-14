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


def test_the_summary_of_a_finished_run_counts_every_step() -> None:
    executor, _ = executor_with_client(reactions={})

    assert error_of_bounded_run(executor) is None

    summary = executor.run_summary(failure_reason=None)
    assert (summary.completed_steps, summary.restored_steps) == (2, 0)


def test_the_summary_of_a_restored_run_counts_the_restored_steps_apart() -> None:
    executor, fake_client = executor_with_client(reactions={}, restore=True)

    assert error_of_bounded_run(executor) is None

    # step 0 is restored, so the run continues with step 1
    assert fake_client.received_steps() == [1]
    summary = executor.run_summary(failure_reason=None)
    assert (summary.completed_steps, summary.restored_steps) == (2, 1)
