from ecosim_client_fmu_v2.fmu2_config import FMU2Config
from tests.tech.resource_utils import config_parser_for_resource


# #SPEC
def test_load() -> None:
    config_parser = config_parser_for_resource('client_config.ini')
    config = FMU2Config.of_config_parser(config_parser)

    # FMU
    assert str(config.fmu_file).endswith('/path/to/fmu.fmu'), f"It was {config.fmu_file}"
