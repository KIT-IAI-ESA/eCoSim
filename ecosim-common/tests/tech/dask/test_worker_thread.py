import asyncio
import threading
import time

import dask.distributed as dd
from ecosim_common.tech.dask.worker_thread import on_worker_thread


def runs_outside_an_event_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return True
    return False


def test_on_worker_thread_runs_the_operation_off_the_event_loop(dask_client: dd.Client) -> None:
    results = dask_client.run(on_worker_thread(runs_outside_an_event_loop))

    assert results
    assert all(results.values()), f"The operation stayed on the event loop: {results}"


def block_for_a_minute() -> bool:
    return threading.Event().wait(timeout=60)


def test_on_worker_thread_gives_up_on_an_operation_that_exceeds_its_timeout(dask_client: dd.Client) -> None:
    """The remaining workers still have to be reached, so a timeout is reported rather than raised."""
    started_at = time.monotonic()

    results = dask_client.run(on_worker_thread(block_for_a_minute, timeout_in_seconds=1))

    assert time.monotonic() - started_at < 30, "The operation held the run until it finished on its own"
    assert all(result is None for result in results.values()), f"A timed out operation must report nothing: {results}"
