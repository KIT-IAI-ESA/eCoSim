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


def _messages_of_test_logger(caplog: pytest.LogCaptureFixture) -> list[str]:
    # an error appends the stack trace below the message
    return [record.getMessage().splitlines()[0] for record in caplog.records if record.name == "TestLogger"]


def test_a_message_without_parameters_is_not_formatted(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    logger = ESPLogger("TestLogger")
    logger.error("error - 100% without parameters")
    logger.warning("warning - 100% without parameters")
    logger.info("info - 100% without parameters")
    logger.debug("debug - 100% without parameters")

    assert _messages_of_test_logger(caplog=caplog) == [
        "error - 100% without parameters",
        "warning - 100% without parameters",
        "info - 100% without parameters",
        "debug - 100% without parameters",
    ]


def test_one_parameter_is_inserted_into_the_message(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    logger = ESPLogger("TestLogger")
    logger.error("error - with %s parameters", "111")
    logger.warning("warning - with %s parameters", "222")
    logger.info("info - with %s parameters", "333")
    logger.debug("debug - with %s parameters", "444")

    assert _messages_of_test_logger(caplog=caplog) == [
        "error - with 111 parameters",
        "warning - with 222 parameters",
        "info - with 333 parameters",
        "debug - with 444 parameters",
    ]


def test_two_parameters_are_inserted_into_the_message(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    logger = ESPLogger("TestLogger")
    logger.error("error - with %s %s parameters", "111", "aaa")
    logger.warning("warning - with %s %s parameters", "222", "bbb")
    logger.info("info - with %s %s parameters", "333", "ccc")
    logger.debug("debug - with %s %s parameters", "444", "ddd")

    assert _messages_of_test_logger(caplog=caplog) == [
        "error - with 111 aaa parameters",
        "warning - with 222 bbb parameters",
        "info - with 333 ccc parameters",
        "debug - with 444 ddd parameters",
    ]
