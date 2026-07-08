from distributed import WorkerPlugin, Worker
from ecosim_common.tech.logger.logger import init_logger


class DaskLoggingPlugin(WorkerPlugin):

    def __init__(self, log_level: int) -> None:
        self._log_level = log_level

    def setup(self, worker: Worker) -> None:
        # runs once per worker process on startup
        init_logger(self._log_level)
