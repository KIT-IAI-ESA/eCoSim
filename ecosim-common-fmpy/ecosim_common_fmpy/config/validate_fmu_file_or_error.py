import logging

from ecosim_common.client.config.client_config import ClientInterfaceConfig, SimulatorConfig
from ecosim_common.config import config_parser
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_common_fmpy.tech.read_model_description import read_model_description


def validate_fmu_file_or_error(
    config: config_parser.ConfigParser,
    fmi_major_version: int,
) -> None:
    logger = logging.getLogger("ecosim_common_fmpy")
    fmu2_config = FMUBaseConfig.of_config_parser(config)
    logger.debug("validate-fmu-file-only flag set -> only checking the FMU file and the .fmc interfaces and then exiting")
    logger.info("Validating FMU file...")
    try:
        model_description = read_model_description(file=fmu2_config.fmu_file, validate=True)
        simulator_config = SimulatorConfig.of_config_parser(config)
        interface_config = ClientInterfaceConfig.of_simulator_config(simulator_config=simulator_config, config_path=config.config_file.parent)
        input_names = interface_config.input_interface_names()
        output_names = interface_config.output_interface_names()
        fmu2_config.ensure_fmu_is_supported(
            model_description=model_description,
            interface_names=[*input_names, *output_names],
            fmi_major_version=fmi_major_version,
        )
        fmu2_config.ensure_interfaces_exist(model_description=model_description, input_names=input_names, output_names=output_names)
    except Exception as e:
        logger.error("Checking FMU file failed: %s", e)
        raise e
    logger.info("Validating FMU file...completed. No errors found.")
    return
