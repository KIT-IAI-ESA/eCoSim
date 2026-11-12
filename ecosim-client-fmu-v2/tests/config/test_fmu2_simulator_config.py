import re
from pathlib import Path

import pytest
from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import fmu2_model_path
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
    interface_names = ["Float64_continuous_input", "Int32_input", "Boolean_output", "String_input", "Enumeration_output"]
    not_real = "Int32_input (Integer), Boolean_output (Boolean), String_input (String), Enumeration_output (Enumeration)"

    with pytest.raises(TypeError, match=re.escape(f"not Real: {not_real}")):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=FMUBaseConfig(fmu_file=fmu2_model_path()), interface_names=interface_names)


def test_interfaces_that_are_no_input_or_output_of_the_fmu_are_rejected() -> None:
    fmu_file = fmu2_model_path()
    interface_names = ["Float64_continuous_input", "Float64_continuous_outptu", "Float64_fixed_parameter"]
    missing = "Float64_continuous_outptu, Float64_fixed_parameter"

    with pytest.raises(ValueError, match=re.escape(f"{fmu_file} has no input or output for these interfaces: {missing}")):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=FMUBaseConfig(fmu_file=fmu_file), interface_names=interface_names)
