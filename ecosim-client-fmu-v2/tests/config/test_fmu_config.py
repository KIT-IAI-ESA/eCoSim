import os
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser

from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import config_parser_for_resource


# #SPEC
def test_load() -> None:
    config_parser = config_parser_for_resource("fmu_v2/client_config.ini")
    config = FMUBaseConfig.of_config_parser(config_parser)

    # FMU
    assert str(config.fmu_file).endswith(os.path.join("path", "to", "fmu.fmu")), f"It was {config.fmu_file}"


def test_the_start_values_keep_the_case_of_their_names(tmp_path: Path) -> None:
    config_file = tmp_path / "preferences.ini"
    config_file.write_text("[fmu]\nfmu_file = [house.fmu]\n[start_values]\nU_wall = 0.3\n", encoding="utf-8")

    assert FMUBaseConfig.of_config_parser(ConfigParser(config_file)).start_value_texts == {"U_wall": "0.3"}
