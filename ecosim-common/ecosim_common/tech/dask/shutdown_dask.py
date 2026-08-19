import asyncio

from dask import distributed
from ecosim_common.tech.shutdown_manager import ShutdownManager


def shutdown_dask_workers(client: distributed.Client) -> None:
    """Shuts down the 'ShutdownManager' of every worker of the given client."""
    client.run(_shutdown_worker)


async def _shutdown_worker() -> None:
    """
    Shuts down the worker's own 'ShutdownManager'.

    Must stay a coroutine: 'Client.run' calls a plain function on the worker's event loop thread, and
    'SyncMethodMixin.sync' hands back an un-awaited coroutine instead of blocking whenever it is
    already inside that loop. The whole shutdown - setting dask events, writing the close sentinel,
    unpublishing datasets - would then silently do nothing. Awaiting a worker thread keeps the loop
    free, so those calls block and take effect as intended.

    It must also stay a module level function: a bound method would pickle the calling process'
    singleton - including its non-picklable 'threading.Event' - and shut down that copy instead of
    the worker's own instance.
    """
    await asyncio.to_thread(ShutdownManager().set_shutdown_at_application_end)
