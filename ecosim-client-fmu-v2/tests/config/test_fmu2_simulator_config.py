import re
from pathlib import Path

import pytest
from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path
from ecosim_test_common.test_data.generate_broken_fmu import generate_broken_fmu


def test_retry_reads_a_model_description_that_fails_the_schema(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # the retry extracts the FMU into ./failed_fmus
    monkeypatch.chdir(tmp_path)
    # fmpy finds ./modelDescription.xml only in the extracted FMU
    fmu_file = generate_broken_fmu(fmu_file=fmu2_model_path(), directory=tmp_path, model_description_entry="./modelDescription.xml")

    model_description = FMU2SimulatorConfig.read_model_description(fmu_config=FMUBaseConfig(fmu_file=fmu_file))

    assert model_description.modelName == "Feedthrough"


def test_interfaces_that_are_not_real_are_rejected() -> None:
    input_names = ["Float64_continuous_input", "Int32_input", "String_input"]
    output_names = ["Boolean_output", "Enumeration_output"]
    not_real = "Int32_input (Integer), Boolean_output (Boolean), String_input (String), Enumeration_output (Enumeration)"

    with pytest.raises(TypeError, match=re.escape(f"not Real: {not_real}")):
        FMU2SimulatorConfig.of(
            simulator_name="test_simulator",
            fmu_config=FMUBaseConfig(fmu_file=fmu2_model_path()),
            input_names=input_names,
            output_names=output_names,
        )


def test_interfaces_that_are_no_input_or_output_of_the_fmu_are_rejected() -> None:
    fmu_file = fmu2_model_path()
    input_names = ["Float64_continuous_input", "Float64_fixed_parameter"]
    output_names = ["Float64_continuous_outptu"]

    with pytest.raises(ValueError, match=re.escape(f"{fmu_file} has no input Float64_fixed_parameter and no output Float64_continuous_outptu")):
        FMU2SimulatorConfig.of(
            simulator_name="test_simulator",
            fmu_config=FMUBaseConfig(fmu_file=fmu_file),
            input_names=input_names,
            output_names=output_names,
        )


def test_an_fmu_output_listed_as_an_input_is_rejected() -> None:
    fmu_config = FMUBaseConfig(fmu_file=fmu2_model_path())

    with pytest.raises(ValueError, match="has no input Float64_continuous_output"):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=["Float64_continuous_output"], output_names=[])


def test_an_fmi_3_fmu_is_rejected() -> None:
    fmu_config = FMUBaseConfig(fmu_file=fmu3_model_path())

    with pytest.raises(ValueError, match=re.escape("is FMI 3.0, but this client runs FMI 2 FMUs only")):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=["u"], output_names=["y"])


def test_an_fmu_input_listed_as_an_output_is_rejected() -> None:
    fmu_config = FMUBaseConfig(fmu_file=fmu2_model_path())

    with pytest.raises(ValueError, match="has no output Float64_continuous_input"):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=[], output_names=["Float64_continuous_input"])
