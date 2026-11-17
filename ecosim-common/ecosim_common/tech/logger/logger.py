import io
import logging
import sys

default_log_format = "%(asctime)s - %(levelname)s - %(name)s: %(message)s"
default_handlers = [logging.StreamHandler()]


def init_logger(log_level: int = logging.INFO) -> None:
    _flush_stdout_after_every_line()
    # Reset any existing logging configuration - this was implemented due to no logging in unittests
    # logging.root.handlers.clear()

    logging.basicConfig(
        level=log_level,
        format=default_log_format,
        handlers=default_handlers,
    )

    root = logging.getLogger()
    root.setLevel(log_level)

    # log levels of python SDK logs
    logging.getLogger("asyncio").setLevel(logging.ERROR)
    logging.getLogger("asyncio.coroutines").setLevel(logging.ERROR)
    # log levels of logger from 3rd party libraries
    logging.getLogger("websockets.server").setLevel(logging.ERROR)
    logging.getLogger("websockets.client").setLevel(logging.ERROR)
    logging.getLogger("websockets.protocol").setLevel(logging.ERROR)
    logging.getLogger("distributed").setLevel(logging.ERROR)
    logging.getLogger("distributed.worker").setLevel(logging.ERROR)


def _flush_stdout_after_every_line() -> None:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)


class ESPLogger:
    def __init__(
        self,
        name: str,
    ):
        self._name = name
        self._logger = logging.getLogger(name)

    @property
    def is_debug_enabled(self) -> bool:
        return self._logger.isEnabledFor(logging.DEBUG)

    def error(
        self,
        message: str,
        *args: object,
    ) -> None:
        self._logger.error(message, *args)

    def exception(
        self,
        message: str,
        *args: object,
    ) -> None:
        self._logger.error(message, *args, exc_info=self.is_debug_enabled)

    def warning(
        self,
        message: str,
        *args: object,
    ) -> None:
        if not self._logger.isEnabledFor(logging.WARNING):
            return
        self._logger.warning(message, *args)

    def info(
        self,
        message: str,
        *args: object,
    ) -> None:
        if not self._logger.isEnabledFor(logging.INFO):
            return
        self._logger.info(message, *args)

    def debug(
        self,
        message: str,
        *args: object,
    ) -> None:
        if not self._logger.isEnabledFor(logging.DEBUG):
            return
        self._logger.debug(message, *args)
