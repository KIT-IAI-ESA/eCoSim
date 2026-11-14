from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig


def test_the_written_fmu_section_reads_back_the_same_fmu_file(tmp_path: Path) -> None:
    fmu_config = FMUBaseConfig(fmu_file=tmp_path / "house.fmu")
    (tmp_path / "preferences.ini").write_text(fmu_config.as_string())

    assert FMUBaseConfig.of_config_parser(config_parser=ConfigParser(tmp_path / "preferences.ini")) == fmu_config
