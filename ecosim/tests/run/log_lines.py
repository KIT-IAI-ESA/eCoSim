import logging

from ecosim_common.tech.logger.logger import default_log_format


def log_line(level: str, logger: str, message: str) -> str:
    """A line as the logger of eCoSim writes it."""
    record = logging.LogRecord(name=logger, level=logging.getLevelName(level), pathname="", lineno=0, msg=message, args=None, exc_info=None)
    return logging.Formatter(fmt=default_log_format).format(record)
