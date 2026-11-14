import re
import shutil
from pathlib import Path
from typing import Iterator

import pytest
from ecosim_client_fmu_v3.fmu3_simulator_config import FMU3SimulatorConfig
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path
from ecosim_test_common.test_data.generate_broken_fmu import generate_broken_fmu

from tests.tech.resource_utils import resource_path

_FEEDTHROUGH_FMU = resource_path() / "test_fmus/Feedthrough.fmu"


@pytest.fixture
def feedthrough_config() -> Iterator[FMU3SimulatorConfig]:
    """The FMI 3 Feedthrough FMU with a .fmc file that lists none of its interfaces, extracted only for the test."""
    simulator_config = FMU3SimulatorConfig.of(
        simulator_name="test_simulator",
        fmu_config=FMUBaseConfig(fmu_file=_FEEDTHROUGH_FMU),
        input_names=[],
        output_names=[],
    )
    yield simulator_config
    shutil.rmtree(simulator_config.unzip_dir, ignore_errors=True)


def test_reads_a_model_description_that_fails_the_schema(tmp_path: Path) -> None:
    fmu_config = FMUBaseConfig(fmu_file=generate_broken_fmu(fmu_file=fmu3_model_path(), directory=tmp_path))

    simulator_config = FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=[], output_names=[])

    assert simulator_config.model_name() == "StateSpace"


def test_interfaces_that_are_no_input_or_output_of_the_fmu_are_rejected() -> None:
    fmu_file = fmu3_model_path()

    with pytest.raises(ValueError, match=re.escape(f"{fmu_file} has no output yy")):
        FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=FMUBaseConfig(fmu_file=fmu_file), input_names=["u"], output_names=["yy"])


def test_interfaces_that_are_not_float64_are_rejected() -> None:
    input_names = ["Float64_continuous_input", "Int32_input", "String_input"]
    output_names = ["Boolean_output", "Enumeration_output"]
    not_float64 = "Int32_input (Int32), Boolean_output (Boolean), String_input (String), Enumeration_output (Enumeration)"
    fmu_config = FMUBaseConfig(fmu_file=_FEEDTHROUGH_FMU)

    with pytest.raises(TypeError, match=re.escape(f"not Float64: {not_float64}")):
        FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=input_names, output_names=output_names)


def test_an_fmi_2_fmu_is_rejected() -> None:
    fmu_config = FMUBaseConfig(fmu_file=fmu2_model_path())

    with pytest.raises(ValueError, match=re.escape("is FMI 2.0, but this client runs FMI 3 FMUs only")):
        FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=["Float64_continuous_input"], output_names=[])


def test_an_input_of_the_simulation_config_that_the_fmu_lacks_is_named_with_the_close_name(feedthrough_config: FMU3SimulatorConfig) -> None:
    reason = feedthrough_config.reason_the_model_cannot_run(
        server_interface_settings=ServerInterfaceSettings(inputs=["Float64_continuous_inptu"], outputs=[]),
    )

    assert reason == (
        f"The simulation config does not fit the model. The FMU {_FEEDTHROUGH_FMU} has no input Float64_continuous_inptu. "
        + "Did you mean Float64_continuous_input?"
    )


def test_an_fmu_input_that_the_fmc_file_does_not_list_is_no_problem_for_the_model(feedthrough_config: FMU3SimulatorConfig) -> None:
    settings = ServerInterfaceSettings(inputs=["Float64_continuous_input"], outputs=["Float64_continuous_output"])

    assert feedthrough_config.reason_the_model_cannot_run(server_interface_settings=settings) is None
