import logging

import fmpy
from ecosim_common.config import config_parser
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig


def validate_fmu_file_or_error(
    config: config_parser.ConfigParser,
) -> None:
    logger = logging.getLogger("ecosim_common_fmpy")
    fmu2_config = FMUBaseConfig.of_config_parser(config)
    logger.debug("validate-fmu-file-only flag set -> only checking FMU file and then exiting")
    logger.info("Validating FMU file...")
    try:
        fmpy.read_model_description(fmu2_config.fmu_file, validate=True)
    except Exception as e:
        logger.error(f"Checking FMU file failed: {e}")
        raise e
    logger.info("Validating FMU file...completed. No errors found.")
    return
