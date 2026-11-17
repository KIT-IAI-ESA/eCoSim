from pathlib import Path

import pytest
from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_client_fmu_v3.fmu3_simulator_config import FMU3SimulatorConfig
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.test_data.spy_fmu_instance import SpyFMUInstance
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config

from tests.tech.resource_utils import resource_path


def _create_client_with_spy(fmu_instance: SpyFMUInstance, is_initialized: bool) -> FMU3Client:
    fmu_config = FMUBaseConfig(fmu_file=resource_path() / "test_fmus/StateSpace.fmu")
    return FMU3Client(
        _client_config=generate_mocked_client_config(),
        _simulation_config=FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=[], output_names=[]),
        _fmu_instance=fmu_instance,
        _is_initialized=is_initialized,
    )


def _create_feedthrough_client_with_spy(fmu_instance: SpyFMUInstance, start_value_texts: dict[str, str]) -> FMU3Client:
    fmu_config = FMUBaseConfig(fmu_file=resource_path() / "test_fmus/Feedthrough.fmu", start_value_texts=start_value_texts)
    return FMU3Client(
        _client_config=generate_mocked_client_config(),
        _simulation_config=FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=[], output_names=[]),
        _fmu_instance=fmu_instance,
    )


def _unzip_dir(client: FMU3Client) -> Path:
    return Path(client._simulation_config.unzip_dir)  # noqa: SLF001


def test_a_failing_terminate_still_frees_the_fmu_and_removes_the_extracted_files() -> None:
    fmu_instance = SpyFMUInstance(terminate_fails=True)
    client = _create_client_with_spy(fmu_instance=fmu_instance, is_initialized=True)

    with pytest.raises(RuntimeError):
        client.on_app_shutdown()

    assert fmu_instance.is_freed
    assert not _unzip_dir(client).exists()


def test_an_fmu_whose_initialization_failed_is_still_freed() -> None:
    fmu_instance = SpyFMUInstance()
    client = _create_client_with_spy(fmu_instance=fmu_instance, is_initialized=False)

    client.on_app_shutdown()

    assert fmu_instance.is_freed


def test_an_array_input_with_the_wrong_number_of_values_is_rejected() -> None:
    client = _create_client_with_spy(fmu_instance=SpyFMUInstance(), is_initialized=True)

    with pytest.raises(ValueError, match="The input u takes 3 values, but got 2"):
        client._set_input_float_matrix(name="u", value=[1.0, 2.0])  # noqa: SLF001
    client.on_app_shutdown()


def test_an_input_the_fmu_lacks_is_the_reason_the_client_does_not_start() -> None:
    client = _create_client_with_spy(fmu_instance=SpyFMUInstance(), is_initialized=False)

    reason = client._reason_the_model_cannot_run(server_interface_settings=ServerInterfaceSettings(inputs=["U"], outputs=[]))  # noqa: SLF001

    assert reason is not None
    assert reason.endswith("has no input U. Did you mean u?")
    client.on_app_shutdown()


def test_a_failing_free_still_removes_the_extracted_files() -> None:
    client = _create_client_with_spy(fmu_instance=SpyFMUInstance(free_instance_fails=True), is_initialized=True)

    client.on_app_shutdown()

    assert not _unzip_dir(client).exists()


def test_a_start_value_reaches_the_fmu_in_time_for_its_initialization() -> None:
    # the FMI 3 Reference FMUs also take a value that is set too late
    fmu_instance = SpyFMUInstance()
    client = _create_feedthrough_client_with_spy(fmu_instance=fmu_instance, start_value_texts={"Float64_fixed_parameter": "2.5"})

    client._initialize_model()  # noqa: SLF001

    assert fmu_instance.start_calls == ["instantiate", "setFloat64 [5] [2.5]", "enterInitializationMode", "exitInitializationMode"]
    client.on_app_shutdown()


def test_the_start_values_are_listed_for_the_start_up_block() -> None:
    client = _create_feedthrough_client_with_spy(fmu_instance=SpyFMUInstance(), start_value_texts={"Float64_fixed_parameter": "2.5"})

    assert client._start_values_for_start_up() == ["Float64_fixed_parameter = 2.5"]  # noqa: SLF001
    client.on_app_shutdown()
