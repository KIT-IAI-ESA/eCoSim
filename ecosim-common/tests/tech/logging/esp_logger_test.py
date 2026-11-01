import logging
from collections.abc import Generator

import pytest
from ecosim_common.tech.logger.logger import ESPLogger, init_logger


@pytest.fixture
def root_at_import_time_level() -> Generator[None, None, None]:
    root = logging.getLogger()
    level_during_tests = root.level
    root.setLevel(logging.WARNING)
    yield
    root.setLevel(level_during_tests)


@pytest.mark.usefixtures("root_at_import_time_level")
def test_logger_created_before_init_logger_emits_debug_records(caplog: pytest.LogCaptureFixture) -> None:
    logger = ESPLogger("CreatedBeforeDebugInit")

    init_logger(log_level=logging.DEBUG)
    logger.debug("debug record")

    assert "debug record" in caplog.messages


@pytest.mark.usefixtures("root_at_import_time_level")
def test_logger_created_before_init_logger_follows_the_info_level(caplog: pytest.LogCaptureFixture) -> None:
    logger = ESPLogger("CreatedBeforeInfoInit")

    init_logger(log_level=logging.INFO)
    logger.info("info record")
    logger.debug("debug record")

    assert "info record" in caplog.messages
    assert "debug record" not in caplog.messages


@pytest.mark.usefixtures("root_at_import_time_level")
def test_overwrite_logger_created_before_init_logger_follows_the_level(capsys: pytest.CaptureFixture[str]) -> None:
    logger = ESPLogger("CreatedBeforeOverwriteInit")

    init_logger(log_level=logging.INFO)
    logger.info("info record", overwrite_last_line=True)
    logger.debug("debug record", overwrite_last_line=True)

    written = capsys.readouterr().err
    assert "info record" in written
    assert "debug record" not in written


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
