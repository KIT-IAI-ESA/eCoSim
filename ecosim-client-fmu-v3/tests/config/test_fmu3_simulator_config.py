import re
from pathlib import Path

import pytest
from ecosim_client_fmu_v3.fmu3_simulator_config import FMU3SimulatorConfig
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import fmu3_model_path
from ecosim_test_common.test_data.generate_broken_fmu import generate_broken_fmu

from tests.tech.resource_utils import resource_path


def test_reads_a_model_description_that_fails_the_schema(tmp_path: Path) -> None:
    fmu_config = FMUBaseConfig(fmu_file=generate_broken_fmu(fmu_file=fmu3_model_path(), directory=tmp_path))

    simulator_config = FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, interface_names=[])

    assert simulator_config.model_name() == "StateSpace"


def test_interfaces_that_are_no_input_or_output_of_the_fmu_are_rejected() -> None:
    fmu_file = fmu3_model_path()

    with pytest.raises(ValueError, match=re.escape(f"{fmu_file} has no input or output for these interfaces: yy")):
        FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=FMUBaseConfig(fmu_file=fmu_file), interface_names=["u", "yy"])


def test_interfaces_that_are_not_float64_are_rejected() -> None:
    interface_names = ["Float64_continuous_input", "Int32_input", "Boolean_output", "String_input", "Enumeration_output"]
    not_float64 = "Int32_input (Int32), Boolean_output (Boolean), String_input (String), Enumeration_output (Enumeration)"
    fmu_config = FMUBaseConfig(fmu_file=resource_path() / "test_fmus/Feedthrough.fmu")

    with pytest.raises(TypeError, match=re.escape(f"not Float64: {not_float64}")):
        FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, interface_names=interface_names)
