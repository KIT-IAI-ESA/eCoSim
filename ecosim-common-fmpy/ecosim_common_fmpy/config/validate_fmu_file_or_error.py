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
    model_description = read_model_description(file=fmu2_config.fmu_file, validate=True)
    simulator_config = SimulatorConfig.of_config_parser(config)
    interface_config = ClientInterfaceConfig.of_simulator_config(simulator_config=simulator_config, config_path=config.config_file.parent)
    fmu2_config.ensure_model_runs_interfaces(
        model_description=model_description,
        input_names=interface_config.input_interface_names(),
        output_names=interface_config.output_interface_names(),
        fmi_major_version=fmi_major_version,
    )
    logger.info("Validating FMU file...completed. No errors found.")
    return
