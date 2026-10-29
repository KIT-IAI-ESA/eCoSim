from pathlib import Path

import pytest
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.executing_platform import ExecutingPlatform
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData


def _referenced_file(config: ConfigParser, section: str, option: str) -> Path:
    return config.config_file.parent / config.get_string_array(section, option)[0]


@pytest.mark.parametrize("platform", HouseSimulationData.PLATFORMS)
@pytest.mark.parametrize("module", HouseSimulationData.MODULES)
def test_every_module_has_a_client_config_with_its_model_files(platform: ExecutingPlatform, module: str) -> None:
    config_file = HouseSimulationData.client_config_file(module, platform)

    assert config_file.parent.name == platform.value
    config = ConfigParser(config_file)
    assert _referenced_file(config, "simulator", "fmc_file").is_file()
    assert _referenced_file(config, "fmu", "fmu_file").is_file()


def test_the_client_configs_default_to_the_current_platform() -> None:
    assert HouseSimulationData.client_config_file("house").parent.name == ExecutingPlatform.current().value
