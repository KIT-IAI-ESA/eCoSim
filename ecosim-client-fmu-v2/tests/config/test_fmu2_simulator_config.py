import re
import shutil
from pathlib import Path
from typing import Iterator

import pytest
from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path, resource_path_file
from ecosim_test_common.test_data.generate_broken_fmu import generate_broken_fmu


@pytest.fixture
def feedthrough_config() -> Iterator[FMU2SimulatorConfig]:
    """The FMI 2 Feedthrough FMU with a .fmc file that lists none of its interfaces, extracted only for the test."""
    simulator_config = FMU2SimulatorConfig.of(
        simulator_name="test_simulator",
        fmu_config=FMUBaseConfig(fmu_file=fmu2_model_path()),
        input_names=[],
        output_names=[],
    )
    yield simulator_config
    shutil.rmtree(simulator_config.unzip_dir(), ignore_errors=True)


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

    with pytest.raises(ValueError, match=re.escape("has no input Float64_continuous_output. Float64_continuous_output is an output of the FMU.")):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=["Float64_continuous_output"], output_names=[])


def test_an_fmi_3_fmu_is_rejected() -> None:
    fmu_config = FMUBaseConfig(fmu_file=fmu3_model_path())

    with pytest.raises(ValueError, match=re.escape("is FMI 3.0, but this client runs FMI 2 FMUs only")):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=["u"], output_names=["y"])


def test_an_fmu_input_listed_as_an_output_is_rejected() -> None:
    fmu_config = FMUBaseConfig(fmu_file=fmu2_model_path())

    with pytest.raises(ValueError, match=re.escape("has no output Float64_continuous_input. Float64_continuous_input is an input of the FMU.")):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=[], output_names=["Float64_continuous_input"])


@pytest.mark.parametrize(
    ("fmu_file", "misspelt_input", "fmu_input"),
    [
        (fmu2_model_path(), "Float64_continuous_inptu", "Float64_continuous_input"),
        # two swapped letters make a short name less alike than one letter does in a long name
        (resource_path_file("fmu_v2/models/house/linux/house.fmu"), "T_otu", "T_out"),
    ],
)
def test_an_fmc_input_the_fmu_lacks_gets_the_close_fmu_name(fmu_file: Path, misspelt_input: str, fmu_input: str) -> None:
    fmu_config = FMUBaseConfig(fmu_file=fmu_file)

    with pytest.raises(ValueError, match=re.escape(f"has no input {misspelt_input}. Did you mean {fmu_input}?")):
        FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=[misspelt_input], output_names=[])


def test_with_several_names_the_fmu_lacks_a_hint_names_the_one_it_replaces() -> None:
    fmu_config = FMUBaseConfig(fmu_file=fmu2_model_path())

    with pytest.raises(ValueError, match=re.escape("Did you mean Float64_continuous_input instead of Float64_continuous_inptu?")):
        FMU2SimulatorConfig.of(
            simulator_name="test_simulator",
            fmu_config=fmu_config,
            input_names=["Float64_continuous_inptu", "T_out"],
            output_names=[],
        )


def test_an_input_of_the_simulation_config_that_the_fmu_lacks_is_named_with_the_close_name(feedthrough_config: FMU2SimulatorConfig) -> None:
    reason = feedthrough_config.reason_the_model_cannot_run(
        server_interface_settings=ServerInterfaceSettings(inputs=["Float64_continuous_inptu"], outputs=[]),
    )

    assert reason == (
        f"The simulation config does not fit the model. The FMU {fmu2_model_path()} has no input Float64_continuous_inptu. "
        + "Did you mean Float64_continuous_input?"
    )


def test_an_fmu_input_that_the_fmc_file_does_not_list_is_no_problem_for_the_model(feedthrough_config: FMU2SimulatorConfig) -> None:
    settings = ServerInterfaceSettings(inputs=["Float64_continuous_input"], outputs=["Float64_continuous_output"])

    assert feedthrough_config.reason_the_model_cannot_run(server_interface_settings=settings) is None


def test_a_simulation_config_interface_of_a_type_the_client_cannot_run_is_a_problem(feedthrough_config: FMU2SimulatorConfig) -> None:
    reason = feedthrough_config.reason_the_model_cannot_run(server_interface_settings=ServerInterfaceSettings(inputs=[], outputs=["Int32_output"]))

    assert reason is not None
    assert reason.endswith("these interfaces are not Real: Int32_output (Integer).")
