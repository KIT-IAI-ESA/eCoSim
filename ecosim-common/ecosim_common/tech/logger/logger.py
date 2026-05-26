import logging
import sys
import traceback
from logging import StreamHandler
from typing import Any

default_log_format = '%(asctime)s - %(levelname)s - %(message)s'
default_handlers = [logging.StreamHandler()]


def init_logger(log_level: int = logging.INFO) -> None:
    # Reset any existing logging configuration - this was implemented due to no logging in unittests
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=log_level,
        format=default_log_format,
        handlers=default_handlers,
    )

    # log levels of python SDK logs
    logging.getLogger('asyncio').setLevel(logging.ERROR)
    logging.getLogger('asyncio.coroutines').setLevel(logging.ERROR)
    # log levels of logger from 3rd party libraries
    logging.getLogger('websockets.server').setLevel(logging.ERROR)
    logging.getLogger('websockets.client').setLevel(logging.ERROR)
    logging.getLogger('websockets.protocol').setLevel(logging.ERROR)
    logging.getLogger('distributed').setLevel(logging.ERROR)
    logging.getLogger('distributed.worker').setLevel(logging.ERROR)


class ESPLogger:
    def __init__(
        self,
        name: str,
    ):
        self.__name = name
        self.__logger = logging.getLogger(name)
        self.__overwrite_logger = logging.getLogger(name + '_overwrite')
        self.__overwrite_logger.handlers = [
            handler for handler in default_handlers if  # type: ignore
            not isinstance(handler, StreamHandler)
        ] + [OverwriteStreamHandler(logging.Formatter(default_log_format))]
        self.__overwrite_logger.propagate = False

    def error(
        self,
        message: str,
    ) -> None:
        stack_trace = ''.join(traceback.format_stack())
        self.__logger.error(f"{self.__name}: {message}\n           Stack trace: {stack_trace}")

    def warning(
        self,
        message: str,
    ) -> None:
        self.__logger.warning(f"{self.__name}: {message}")

    def info(
        self,
        message: str,
        overwrite_last_line: bool = False,
    ) -> None:
        message = f"{self.__name}: {message}"
        if overwrite_last_line:
            self.__overwrite_logger.info(message)
        else:
            self.__logger.info(message)

    def debug(
        self,
        message: str,
        overwrite_last_line: bool = False,
    ) -> None:
        message = f"{self.__name}: {message}"
        if overwrite_last_line:
            self.__overwrite_logger.debug(message)
        else:
            self.__logger.debug(message)


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
        sys.stderr.write('\r' + msg)  # Use carriage return to overwrite the line
        sys.stderr.flush()
