import logging
from typing import Any, Generator

import pytest

from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager


@pytest.fixture(scope="session", autouse=True)
def setup_logging() -> None:
    """runs once before all tests"""
    ShutdownManager().init()
    init_logger(log_level=logging.DEBUG)


@pytest.fixture(scope="session", autouse=True)
def teardown_shutdown_manager() -> Generator[None, Any, None]:
    """runs once after all tests"""
    yield
    ShutdownManager().set_shutdown_at_application_end()
