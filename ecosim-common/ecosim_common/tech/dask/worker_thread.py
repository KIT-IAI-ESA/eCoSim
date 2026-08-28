import asyncio
from typing import Awaitable, Callable, TypeVar

import dask.distributed as distributed
from dask.utils import funcname
from ecosim_common.tech.logger.logger import ESPLogger

_logger = ESPLogger("WorkerThread")

_Result = TypeVar("_Result")


def on_worker_thread(
    operation: Callable[[], _Result],
    timeout_in_seconds: float | None = None,
) -> Callable[..., Awaitable[_Result | None]]:
    """
    Wraps 'operation' for 'Client.run', which would otherwise run it on the worker's event loop thread.

    A dask call cannot block on that thread - it would wait on the very loop that has to carry it - so dask
    hands back an un-awaited coroutine instead and the call silently does nothing. The wrapper awaits a
    worker thread, which keeps the loop free, so the call blocks and takes effect as intended.

    'Client.run' also runs out of band, without the worker in the context 'distributed.get_client' reads, so
    dask primitives like 'distributed.Event' find no client at all. 'dask_worker' is the worker dask passes
    into the wrapper, and asking it for its client registers that client as the default one of the process,
    which is the next place those primitives look.

    Without a timeout the wrapper waits for as long as 'operation' takes. A timeout bounds the waiting, not
    the work: a thread cannot be cancelled, so a stuck operation keeps running in the background.

    There is also some 'dask magic' going on, notably the following excerpt from Client.run:

        If your function takes an input argument named ``dask_worker`` then
        that variable will be populated with the worker itself.

    That means, the dask_worker argument is populated with the worker itself and can be
    used within the operation - even though the caller does not explicitly pass it.
    """

    async def call_on_worker_thread(dask_worker: distributed.Worker | None = None) -> _Result | None:
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(_call_with_the_workers_client, operation, dask_worker),
                timeout=timeout_in_seconds,
            )
        except TimeoutError:
            # raising would abort 'Client.run' and leave the remaining workers untouched
            _logger.error("'%s' took longer than %ss on this worker -> giving up on waiting for it.", funcname(operation), timeout_in_seconds)
            return None

    return call_on_worker_thread


def _call_with_the_workers_client(
    operation: Callable[[], _Result],
    dask_worker: distributed.Worker | None,
) -> _Result:
    if dask_worker is not None:
        dask_worker.client  # registers the worker's client as the default one of this process
    return operation()
