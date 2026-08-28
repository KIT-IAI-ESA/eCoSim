from dask import distributed
from ecosim_common.communication.dask.dask_logging_plugin import DaskLoggingPlugin
from ecosim_common.tech.dask.class_serializer import serialize_classes
from ecosim_common.tech.shutdown_manager import ShutdownManager


def init_dask(
    log_level: int,
    client: distributed.Client | None = None,
) -> None:
    """
    The worker logging is deliberately *not* forwarded to the client.

    'DaskLoggingPlugin' gives every worker its own handler, so each worker writes its records itself.
    'Client.forward_logging' would send those records to the client on top of that, where the logger of
    the same name emits them a second time.
    """

    def shutdown_manager_worker() -> None:
        ShutdownManager().init()

    serialize_classes()
    dask_client = client or distributed.get_client()
    dask_client.run(shutdown_manager_worker)
    dask_client.run(serialize_classes)
    dask_client.register_plugin(DaskLoggingPlugin(log_level=log_level))
