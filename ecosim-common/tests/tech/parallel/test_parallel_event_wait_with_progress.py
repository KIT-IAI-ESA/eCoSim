import threading
import time

import pytest
from ecosim_common.tech.parallel.parallel_event import ParallelEvent, WaitAbortedError


def test_returns_true_when_the_event_is_already_set() -> None:
    assert (
        ParallelEvent.thread(init_set=True).wait_with_progress(
            timeout_in_seconds=1,
            progress_interval_in_seconds=1,
        )
        is True
    )


def test_returns_true_when_the_event_is_set_while_waiting() -> None:
    event = ParallelEvent.thread()
    threading.Timer(0.1, event.set).start()

    assert (
        event.wait_with_progress(
            progress_interval_in_seconds=1,
            timeout_in_seconds=10,
        )
        is True
    )


def test_returns_false_when_the_timeout_passes() -> None:
    assert ParallelEvent.thread().wait_with_progress(timeout_in_seconds=0.2, progress_interval_in_seconds=0.05) is False


def test_does_not_wait_longer_than_the_timeout() -> None:
    event = ParallelEvent.thread()
    start = time.monotonic()

    event.wait_with_progress(
        timeout_in_seconds=0.2,
        progress_interval_in_seconds=10,
    )

    assert time.monotonic() - start < 5


def test_calls_on_progress_while_waiting() -> None:
    event = ParallelEvent.thread()
    progress_calls: list[int] = []

    event.wait_with_progress(
        timeout_in_seconds=0.3,
        progress_interval_in_seconds=0.05,
        on_progress=lambda: progress_calls.append(1),
    )

    assert len(progress_calls) > 0


def test_raises_when_the_abort_condition_becomes_true() -> None:
    event = ParallelEvent.thread()

    with pytest.raises(WaitAbortedError):
        event.wait_with_progress(
            timeout_in_seconds=10,
            progress_interval_in_seconds=0.05,
            abort=lambda: True,
        )


def test_waits_without_a_timeout_until_the_event_is_set() -> None:
    event = ParallelEvent.thread()
    threading.Timer(0.1, event.set).start()

    assert event.wait_with_progress(progress_interval_in_seconds=1) is True
