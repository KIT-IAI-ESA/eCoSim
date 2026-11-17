from pathlib import Path

import pytest
from ecosim_common.client.config.client_type import ClientType
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_common_fmpy.config.fmu_interfaces import FMUInterfaces, SkippedVariable
from ecosim_common_fmpy.tech.read_model_description import read_model_description
from ecosim_test_common.resources.resource_utils import fmu2_model_path, fmu3_model_path, resource_path_file
from ecosim_test_common.test_data.generate_changed_fmu import generate_fmi1_fmu, generate_fmu_without_co_simulation


def test_the_interfaces_of_an_fmi2_fmu_are_its_real_inputs_and_outputs() -> None:
    interfaces = FMUInterfaces.of_fmu_file(fmu_file=fmu2_model_path())

    assert [interface.name for interface in interfaces.inputs] == ["Float64_continuous_input", "Float64_discrete_input"]
    assert [interface.name for interface in interfaces.outputs] == ["Float64_continuous_output", "Float64_discrete_output"]
    assert interfaces.client_type() == ClientType.FMU_2


def test_an_input_is_found_by_its_name_with_its_start_value() -> None:
    interfaces = FMUInterfaces.of_fmu_file(fmu_file=fmu2_model_path())

    continuous_input = interfaces.input_named(name="Float64_continuous_input")

    assert continuous_input is not None
    assert continuous_input.start == "0"
    assert interfaces.input_named(name="Float64_continuous_output") is None


def test_the_variables_the_fmi2_client_cannot_exchange_are_skipped_with_their_type() -> None:
    skipped = FMUInterfaces.of_fmu_file(fmu_file=fmu2_model_path()).skipped

    assert SkippedVariable(name="Int32_input", causality="input", type="Integer") in skipped
    assert {variable.type for variable in skipped} == {"Integer", "Boolean", "String", "Enumeration"}


def test_the_interfaces_of_an_fmi3_fmu_keep_float64_arrays_with_their_shape() -> None:
    interfaces = FMUInterfaces.of_fmu_file(fmu_file=fmu3_model_path())

    assert [(interface.name, interface.shape) for interface in interfaces.inputs + interfaces.outputs] == [("u", (3,)), ("y", (3,))]
    assert interfaces.client_type() == ClientType.FMU_3


def test_an_interface_takes_its_unit_and_description_from_the_model_description() -> None:
    weather = FMUInterfaces.of_fmu_file(fmu_file=resource_path_file("hpc/modules/weather/weather.fmu"))

    dry_bulb_temperature = weather.output_named(name="weatherBus.TDryBul")

    assert dry_bulb_temperature is not None
    assert dry_bulb_temperature.unit == "K"
    assert dry_bulb_temperature.description == "Dry bulb temperature"


@pytest.mark.parametrize(("fmu_file", "fmi_major_version"), [(fmu2_model_path(), 2), (fmu3_model_path(), 3)])
def test_the_client_check_accepts_every_interface_of_the_fmu_interfaces(fmu_file: Path, fmi_major_version: int) -> None:
    interfaces = FMUInterfaces.of_fmu_file(fmu_file=fmu_file)

    FMUBaseConfig(fmu_file=fmu_file).ensure_fmu_is_supported(
        model_description=read_model_description(file=fmu_file),
        interface_names=[interface.name for interface in interfaces.inputs + interfaces.outputs],
        fmi_major_version=fmi_major_version,
    )


def test_an_fmu_for_model_exchange_only_is_rejected(tmp_path: Path) -> None:
    fmu_file = generate_fmu_without_co_simulation(fmu_file=fmu2_model_path(), directory=tmp_path)

    with pytest.raises(ValueError, match="no co-simulation part"):
        FMUInterfaces.of_fmu_file(fmu_file=fmu_file)


def test_an_fmi1_fmu_is_rejected_with_the_versions_that_run(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="is FMI 1.0, but eCoSim runs FMI 2.0 and FMI 3.0 FMUs only"):
        FMUInterfaces.of_fmu_file(fmu_file=generate_fmi1_fmu(directory=tmp_path))
