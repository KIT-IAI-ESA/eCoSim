from dataclasses import dataclass, field
from typing import override
from uuid import uuid4

import dask.distributed as dd
from ecosim_common.tech.dask.shutdown_dask import shutdown_dask_workers
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


def test_shutdown_dask_workers_shuts_down_every_worker(dask_client: dd.Client) -> None:
    shutdown_dask_workers(dask_client)

    def worker_is_shutdown() -> bool:
        return ShutdownManager().is_shutdown()

    worker_states = dask_client.run(worker_is_shutdown)

    assert worker_states
    assert all(worker_states.values()), f"Not every worker was shut down: {worker_states}"


def test_shutdown_dask_workers_completes_the_dask_work_of_the_listeners(dask_client: dd.Client) -> None:
    event_name = f"shutdown_probe_{uuid4()}"

    def register_probe_listener(event_name: str) -> None:
        ShutdownManager().register_listener(DaskEventShutdownListener(_event=ParallelEvent.dask(dask_name=event_name)))

    dask_client.submit(register_probe_listener, event_name, pure=False).result()

    shutdown_dask_workers(dask_client)

    assert ParallelEvent.dask(dask_name=event_name).wait(timeout=10), "The listener never reached the dask event"


def test_shutdown_dask_workers_leaves_the_calling_process_running(dask_client: dd.Client) -> None:
    shutdown_dask_workers(dask_client)

    assert not ShutdownManager().is_shutdown()


@dataclass
class DaskEventShutdownListener(ShutdownListener):
    _event: ParallelEvent = field()

    @override
    def on_app_shutdown(self) -> None:
        self._event.set()
