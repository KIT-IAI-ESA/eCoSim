from ecosim_common.tech.logger.logger import ESPLogger


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
