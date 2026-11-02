import logging
from collections.abc import Generator

import pytest
from ecosim_common.tech.logger.logger import ESPLogger, init_logger


@pytest.fixture
def root_logger_not_initialized_yet() -> Generator[None, None, None]:
    """Sets the root logger to WARNING, its level before `init_logger` runs."""
    root = logging.getLogger()
    level_during_tests = root.level
    root.setLevel(logging.WARNING)
    yield
    root.setLevel(level_during_tests)


@pytest.mark.usefixtures("root_logger_not_initialized_yet")
def test_logger_created_before_init_logger_follows_the_debug_level() -> None:
    logger = ESPLogger("CreatedBeforeDebugInit")

    init_logger(log_level=logging.DEBUG)

    assert logger.is_debug_enabled


@pytest.mark.usefixtures("root_logger_not_initialized_yet")
def test_logger_created_before_init_logger_follows_the_info_level() -> None:
    logger_name = "CreatedBeforeInfoInit"
    logger = ESPLogger(logger_name)

    init_logger(log_level=logging.INFO)

    assert logging.getLogger(logger_name).isEnabledFor(logging.INFO)
    assert not logger.is_debug_enabled


def test_without_parameters() -> None:
    logger = ESPLogger("TestLogger")
    logger.error("error - without parameters")
    logger.warning("warning - without parameters")
    logger.info("info - without parameters")
    logger.debug("debug - without parameters")


def test_with_one_parameter() -> None:
    logger = ESPLogger("TestLogger")
    logger.error("error - with %s parameters", "111")
    logger.warning("warning - with %s parameters", "222")
    logger.info("info - with %s parameters", "333")
    logger.debug("debug - with %s parameters", "444")


def test_with_two_parameter() -> None:
    logger = ESPLogger("TestLogger")
    logger.error("error - with %s %s parameters", "111", "aaa")
    logger.warning("warning - with %s %s parameters", "222", "bbb")
    logger.info("info - with %s %s parameters", "333", "ccc")
    logger.debug("debug - with %s %s parameters", "444", "ddd")
