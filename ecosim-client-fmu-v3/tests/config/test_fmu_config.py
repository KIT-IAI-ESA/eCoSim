from ecosim_client_fmu_v3.fmu3_config import FMU3Config
from tests.tech.resource_utils import config_parser_for_resource


# #SPEC
def test_load() -> None:
    config_parser = config_parser_for_resource('client_config.ini')
    config = FMU3Config.of(config_parser)

    # FMU
    assert str(config.fmu_file).endswith('/path/to/fmu.fmu'), f"It was {config.fmu_file}"
