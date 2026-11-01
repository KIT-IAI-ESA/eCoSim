import logging
import sys
import traceback
from logging import StreamHandler
from typing import Any

default_log_format = "%(asctime)s - %(levelname)s - %(name)s: %(message)s"
default_handlers = [logging.StreamHandler()]

_overwrite_suffix = "_overwrite"


def init_logger(log_level: int = logging.INFO) -> None:
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


class _StripOverwriteSuffixFilter(logging.Filter):
    """Hides the internal '_overwrite' logger suffix from the rendered '%(name)s'."""

    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:
        record.name = record.name.removesuffix(_overwrite_suffix)
        return True


class ESPLogger:
    def __init__(
        self,
        name: str,
    ):
        self._name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.getLogger().level)
        self._overwrite_logger = logging.getLogger(name + _overwrite_suffix)
        self._overwrite_logger.handlers = [
            handler
            for handler in default_handlers
            if not isinstance(handler, StreamHandler)  # type: ignore
        ] + [OverwriteStreamHandler(logging.Formatter(default_log_format))]
        self._overwrite_logger.propagate = False
        self._overwrite_logger.addFilter(_StripOverwriteSuffixFilter())

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
        overwrite_last_line: bool = False,
    ) -> None:
        logger = self._overwrite_logger if overwrite_last_line else self._logger
        if not logger.isEnabledFor(logging.INFO):
            return
        logger.info(message, *args)

    def debug(
        self,
        message: str,
        *args: object,
        overwrite_last_line: bool = False,
    ) -> None:
        logger = self._overwrite_logger if overwrite_last_line else self._logger
        if not logger.isEnabledFor(logging.DEBUG):
            return
        logger.debug(message, *args)


class OverwriteStreamHandler(logging.StreamHandler[Any]):
    def __init__(
        self,
        formatter: logging.Formatter,
    ):
        super().__init__()
        self.formatter = formatter

    def emit(
        self,
        record: logging.LogRecord,
    ) -> None:
        msg = self.format(record)
        sys.stderr.write("\r" + msg)  # Use carriage return to overwrite the line
        sys.stderr.flush()
