from ecosim_server.simulation.step_progress import StepProgress
from ecosim_test_common.test_data.manual_clock import ManualClock
from tests.data.generate_postgres_name_config import generate_simulation_config


def _started_progress(clock: ManualClock, steps: int = 35_040, step_size_in_ms: int = 900_000, first_step: int = 0) -> StepProgress:
    step_progress = StepProgress(
        _simulation_config=generate_simulation_config(clients=[], steps=steps, step_size_in_ms=step_size_in_ms),
        _clock=clock,
    )
    step_progress.start(first_step=first_step)
    return step_progress


def test_the_first_progress_line_comes_after_ten_seconds() -> None:
    clock = ManualClock()
    step_progress = _started_progress(clock=clock)

    clock.advance(seconds=9.9)
    line_before = step_progress.step_completed(completed_steps=100)
    clock.advance(seconds=0.1)
    line_after = step_progress.step_completed(completed_steps=101)

    assert line_before is None
    assert line_after is not None


def test_a_progress_line_names_the_steps_the_simulated_time_the_speed_and_the_time_left() -> None:
    clock = ManualClock()
    step_progress = _started_progress(clock=clock)

    clock.advance(seconds=10)

    assert step_progress.step_completed(completed_steps=3_504) == (
        "Step 3,504 of 35,040 (10 %), simulated 2024-02-06 12:00, 350 steps/s, about 1 min 30 s left"
    )


def test_progress_lines_come_every_10_s_in_the_first_minute_then_every_minute_and_after_an_hour_every_10_minutes() -> None:
    clock = ManualClock()
    step_progress = _started_progress(clock=clock)
    line_times: list[float] = []

    for completed_steps in range(1, 7_201):
        clock.advance(seconds=1)
        if step_progress.step_completed(completed_steps=completed_steps) is not None:
            line_times.append(clock.now)

    assert line_times == [10, 20, 30, 40, 50, 60, *range(120, 3_601, 60), *range(4_200, 7_201, 600)]


def test_the_last_step_gets_no_progress_line() -> None:
    clock = ManualClock()
    step_progress = _started_progress(clock=clock, steps=100)

    clock.advance(seconds=60)

    assert step_progress.step_completed(completed_steps=100) is None


def test_after_a_restore_the_speed_counts_only_the_steps_of_this_run() -> None:
    clock = ManualClock()
    step_progress = _started_progress(clock=clock, first_step=17_520)

    clock.advance(seconds=10)
    line = step_progress.step_completed(completed_steps=18_020)

    assert line is not None
    assert line.startswith("Step 18,020 of 35,040 (51 %), simulated 2024-07-06 17:00, 50 steps/s,")


def test_a_slow_run_shows_the_time_of_one_step() -> None:
    clock = ManualClock()
    step_progress = _started_progress(clock=clock)

    clock.advance(seconds=12)
    line = step_progress.step_completed(completed_steps=1)

    assert line is not None
    assert "12 s per step" in line


def test_a_step_size_below_a_minute_shows_the_seconds_of_the_simulated_time() -> None:
    clock = ManualClock()
    step_progress = _started_progress(clock=clock, step_size_in_ms=1_500)

    clock.advance(seconds=10)
    line = step_progress.step_completed(completed_steps=3)

    assert line is not None
    assert "simulated 2024-01-01 00:00:04" in line


def test_the_step_time_ends_with_the_last_completed_step() -> None:
    clock = ManualClock()
    step_progress = _started_progress(clock=clock)

    clock.advance(seconds=5)
    step_progress.step_completed(completed_steps=1)
    clock.advance(seconds=30)

    assert step_progress.step_time_in_seconds() == 5
