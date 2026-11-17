from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_common_fmpy.tech.read_model_description import read_model_description
from ecosim_test_common.resources.resource_utils import fmu2_model_path


def test_the_written_fmu_section_reads_back_the_same_fmu_file(tmp_path: Path) -> None:
    fmu_config = FMUBaseConfig(fmu_file=tmp_path / "house.fmu")
    (tmp_path / "preferences.ini").write_text(fmu_config.as_string())

    assert FMUBaseConfig.of_config_parser(config_parser=ConfigParser(tmp_path / "preferences.ini")) == fmu_config


def test_the_missing_interfaces_are_the_inputs_and_outputs_the_fmu_does_not_have() -> None:
    missing = FMUBaseConfig.missing_interfaces(
        model_description=read_model_description(file=fmu2_model_path()),
        input_names=["Float64_continuous_input", "missing_input"],
        output_names=["Float64_continuous_output", "missing_output"],
    )

    assert missing == (["missing_input"], ["missing_output"])
