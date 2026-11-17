import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common_fmpy.config.validate_fmu_file_or_error import validate_fmu_file_or_error
from ecosim_test_common.resources.resource_utils import fmu2_model_path, resource_path
from tests.tech import resource_utils


def test_validate_fmu_file_happy_path() -> None:
    main_file = f"{resource_utils.production_source_path().absolute()}/main.py"
    config_file = f"{resource_path().absolute()}/fmu_v2/models/house/linux/heating_preferences_linux.ini"
    print("")
    print(f"Main file: {main_file}")
    print(f"Config file: {config_file}")
    proc = subprocess.Popen(
        [sys.executable, "-u", main_file, "--debug", "--validate-fmu-file-only", "--config-file", config_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    try:
        out, err = proc.communicate(timeout=50)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()

    print("OUT:", out)
    print("ERR:", err)

    assert 0 == proc.returncode


def test_validate_fmu_file_with_error() -> None:
    main_file = f"{resource_utils.production_source_path().absolute()}/main.py"
    config_file = f"{resource_path().absolute()}/fmu_v2/models/house/linux/heating_broken_preferences_linux.ini"
    print("")
    print(f"Main file: {main_file}")
    print(f"Config file: {config_file}")
    proc = subprocess.Popen(
        [sys.executable, "-u", main_file, "--debug", "--validate-fmu-file-only", "--config-file", config_file],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
    )
    try:
        out, err = proc.communicate(timeout=50)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()

    print("OUT:", out)
    print("ERR:", err)

    assert 0 != proc.returncode


def test_validation_fails_for_an_interface_the_fmu_does_not_have(tmp_path: Path) -> None:
    config_directory = shutil.copytree(src=fmu2_model_path().parent, dst=tmp_path / "fmu2") / "configs"
    fmc_file = config_directory / "Feedthrough.fmc"
    fmc_file.write_text(fmc_file.read_text().replace("Float64_continuous_output", "Float64_continuous_outptu"))

    with pytest.raises(ValueError, match="Float64_continuous_outptu"):
        validate_fmu_file_or_error(config=ConfigParser(config_directory / "feedthrough.ini"), fmi_major_version=2)


def test_validation_fails_for_an_interface_that_is_not_real(tmp_path: Path) -> None:
    config_directory = shutil.copytree(src=fmu2_model_path().parent, dst=tmp_path / "fmu2") / "configs"
    fmc_file = config_directory / "Feedthrough.fmc"
    fmc_file.write_text(fmc_file.read_text().replace("Float64_continuous_output", "Int32_output"))

    with pytest.raises(TypeError, match=re.escape("not Real: Int32_output (Integer)")):
        validate_fmu_file_or_error(config=ConfigParser(config_directory / "feedthrough.ini"), fmi_major_version=2)


def test_validation_fails_for_an_fmu_of_the_other_fmi_version(tmp_path: Path) -> None:
    config_directory = shutil.copytree(src=fmu2_model_path().parent, dst=tmp_path / "fmu2") / "configs"

    with pytest.raises(ValueError, match=re.escape("is FMI 2.0, but this client runs FMI 3 FMUs only")):
        validate_fmu_file_or_error(config=ConfigParser(config_directory / "feedthrough.ini"), fmi_major_version=3)


def test_validation_fails_for_swapped_inputs_and_outputs(tmp_path: Path) -> None:
    config_directory = shutil.copytree(src=fmu2_model_path().parent, dst=tmp_path / "fmu2") / "configs"
    fmc_file = config_directory / "Feedthrough.fmc"
    swapped = fmc_file.read_text().replace("Float64_continuous_input", "swap").replace("Float64_continuous_output", "Float64_continuous_input")
    fmc_file.write_text(swapped.replace("swap", "Float64_continuous_output"))

    with pytest.raises(ValueError, match="has no input Float64_continuous_output and no output Float64_continuous_input"):
        validate_fmu_file_or_error(config=ConfigParser(config_directory / "feedthrough.ini"), fmi_major_version=2)


def test_validation_fails_for_a_start_value_the_fmu_does_not_have(tmp_path: Path) -> None:
    config_directory = shutil.copytree(src=fmu2_model_path().parent, dst=tmp_path / "fmu2") / "configs"
    with open(config_directory / "feedthrough.ini", "a", encoding="utf-8") as config_file:
        config_file.write("[start_values]\nFloat64_tunable_paramter = 2.5\n")

    with pytest.raises(ValueError, match=re.escape("Float64_tunable_paramter: not a variable of the FMU. Did you mean Float64_tunable_parameter?")):
        validate_fmu_file_or_error(config=ConfigParser(config_directory / "feedthrough.ini"), fmi_major_version=2)
