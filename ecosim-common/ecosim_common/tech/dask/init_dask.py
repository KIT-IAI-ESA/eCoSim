from dask import distributed
from ecosim_common.communication.dask.dask_logging_plugin import DaskLoggingPlugin
from ecosim_common.tech.dask.class_serializer import serialize_classes
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager


def init_dask(
    log_level: int,
    client: distributed.Client | None = None,
) -> None:
    def init_logger_worker(log_level: int) -> None:
        init_logger(log_level)

    def shutdown_manager_worker() -> None:
        ShutdownManager().init()

    serialize_classes()
    dask_client = client or distributed.get_client()
    dask_client.run(shutdown_manager_worker)
    dask_client.run(serialize_classes)
    dask_client.register_plugin(DaskLoggingPlugin(log_level=log_level))
    dask_client.run(init_logger_worker, log_level)
    dask_client.forward_logging()
