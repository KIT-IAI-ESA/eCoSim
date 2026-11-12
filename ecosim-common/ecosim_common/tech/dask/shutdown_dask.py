from dask import distributed
from ecosim_common.tech.dask.worker_thread import on_worker_thread
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownManager

# a shutting down listener only closes what it already holds, so it either finishes quickly or is stuck
_DEFAULT_SHUTDOWN_TIMEOUT_IN_SECONDS = 30.0
_logger = ESPLogger("ShutdownDask")


def shutdown_dask_workers(
    client: distributed.Client,
    timeout_in_seconds: float = _DEFAULT_SHUTDOWN_TIMEOUT_IN_SECONDS,
) -> None:
    """
    ShutdownManager is a per-process singleton. The HPC run spans many processes: one main process
    plus N dask worker processes, each hosting simulator clients with DaskChannel objects registered
    as shutdown listeners. When the simulation ends, the main process must tell every worker to
    release its own resources.
    """
    try:
        client.run(on_worker_thread(ShutdownManager().set_shutdown_at_application_end, timeout_in_seconds))
    except Exception as error:
        _logger.error("Shutting down the dask workers failed: %s", error)
