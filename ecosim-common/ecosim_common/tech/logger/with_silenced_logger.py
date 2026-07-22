import logging
from contextlib import contextmanager
from typing import Any, Generator


@contextmanager
def silenced_logger(
    logger_name: str,
    level: int = logging.CRITICAL,
) -> Generator[None, Any, None]:
    logger = logging.getLogger(logger_name)
    old = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(old)
