import os

from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import config_parser_for_resource


# #SPEC
def test_load() -> None:
    config_parser = config_parser_for_resource("fmu_v2/client_config.ini")
    config = FMUBaseConfig.of_config_parser(config_parser)

    # FMU
    assert str(config.fmu_file).endswith(os.path.join("path", "to", "fmu.fmu")), f"It was {config.fmu_file}"
