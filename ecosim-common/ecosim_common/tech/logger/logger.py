import io
import logging
import sys
import traceback

default_log_format = "%(asctime)s - %(levelname)s - %(name)s: %(message)s"
default_handlers = [logging.StreamHandler()]


def init_logger(log_level: int = logging.INFO) -> None:
    # what a model prints lands in a log file where it happens, not at the end
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)
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
        if not self._logger.isEnabledFor(logging.ERROR):
            return
        # the stack of the logging call helps to debug, in a normal run it buries the message
        if not self.is_debug_enabled:
            self._logger.error(message, *args)
            return
        stack_trace = "".join(traceback.format_stack())
        self._logger.error(
            "%s\n           Stack trace: %s",
            message % args if args else message,
            stack_trace,
        )

    def exception(
        self,
        message: str,
        *args: object,
    ) -> None:
        self._logger.exception(message, *args)

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
