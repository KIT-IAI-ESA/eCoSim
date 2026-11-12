from pathlib import Path

import pytest
from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_client_fmu_v3.fmu3_simulator_config import FMU3SimulatorConfig
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.test_data.spy_fmu_instance import SpyFMUInstance
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config

from tests.tech.resource_utils import resource_path


def _create_client_with_spy(fmu_instance: SpyFMUInstance, is_initialized: bool) -> FMU3Client:
    fmu_config = FMUBaseConfig(fmu_file=resource_path() / "test_fmus/StateSpace.fmu")
    return FMU3Client(
        _client_config=generate_mocked_client_config(),
        _simulation_config=FMU3SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, interface_names=[]),
        _fmu_instance=fmu_instance,
        _is_initialized=is_initialized,
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


def test_a_failing_free_still_removes_the_extracted_files() -> None:
    client = _create_client_with_spy(fmu_instance=SpyFMUInstance(free_instance_fails=True), is_initialized=True)

    client.on_app_shutdown()

    assert not _unzip_dir(client).exists()
