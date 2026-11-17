from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import resource_path
from ecosim_test_common.test_data.spy_fmu_instance import SpyFMUInstance
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config

_FMU_FILE = resource_path() / "fmu_v2" / "test_fmus" / "Sub1_Linux.fmu"


def _create_client(start_value_texts: dict[str, str] | None = None) -> FMU2Client:
    simulator_config = _create_simulator_config(start_value_texts=start_value_texts)
    return FMU2Client(
        _client_config=generate_mocked_client_config(),
        _channel_or_none=MagicMock(spec=ESPChannel),
        _simulator_config=simulator_config,
        _fmu_instance=simulator_config.create_fmu2_instance(),
    )


def _create_simulator_config(start_value_texts: dict[str, str] | None = None) -> FMU2SimulatorConfig:
    fmu_config = FMUBaseConfig(fmu_file=_FMU_FILE, start_value_texts=start_value_texts or {})
    return FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config, input_names=["pos_2"], output_names=["pos_1"])


def _create_client_with_spy(fmu_instance: SpyFMUInstance, is_initialized: bool, start_value_texts: dict[str, str] | None = None) -> FMU2Client:
    return FMU2Client(
        _client_config=generate_mocked_client_config(),
        _simulator_config=_create_simulator_config(start_value_texts=start_value_texts),
        _fmu_instance=fmu_instance,
        _is_initialized=is_initialized,
    )


def _read_input(client: FMU2Client, name: str) -> list[float]:
    fmu_instance = client._fmu_instance  # noqa: SLF001
    simulator_config = client._simulator_config  # noqa: SLF001
    return fmu_instance.getReal([simulator_config.input_value_references(name)])


def _unzip_dir(client: FMU2Client) -> Path:
    return Path(client._simulator_config.unzip_dir())  # noqa: SLF001


@skip_unless_fmpy_loads(_FMU_FILE)
def test_set_input_float_with_real_fmu() -> None:
    client = _create_client()
    client._initialize_model()  # noqa: SLF001

    client._do_model_step(input_values={"pos_2": 0.3}, step_size_in_seconds=1)  # noqa: SLF001

    assert _read_input(client, "pos_2") == [0.3]
    client.on_app_shutdown()


@skip_unless_fmpy_loads(_FMU_FILE)
@pytest.mark.parametrize("invalid_input", ["0.3", [0.4], [0.5, 0.6], None])
def test_set_invalid_input_with_real_fmu(invalid_input: Any) -> None:
    client = _create_client()
    client._initialize_model()  # noqa: SLF001

    with pytest.raises(TypeError):
        client._do_model_step(input_values={"pos_2": invalid_input}, step_size_in_seconds=1)  # noqa: SLF001

    assert _read_input(client, "pos_2") == [0.0]
    client.on_app_shutdown()


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


@skip_unless_fmpy_loads(_FMU_FILE)
def test_the_fmu_starts_with_a_start_value() -> None:
    client = _create_client(start_value_texts={"mass.s": "1.25"})

    client._initialize_model()  # noqa: SLF001

    # the output pos_1 is the position mass.s
    assert client._get_model_output("pos_1") == 1.25  # noqa: SLF001
    client.on_app_shutdown()


def test_a_start_value_reaches_the_fmu_in_time_for_its_initialization() -> None:
    # FMI 2.0 takes a value with initial="approx" only before enterInitializationMode
    fmu_instance = SpyFMUInstance()
    client = _create_client_with_spy(fmu_instance=fmu_instance, is_initialized=False, start_value_texts={"mass.s": "1.25"})

    client._initialize_model()  # noqa: SLF001

    assert fmu_instance.start_calls == [
        "instantiate",
        "setupExperiment",
        "setReal [369098765] [1.25]",
        "enterInitializationMode",
        "exitInitializationMode",
    ]
    client.on_app_shutdown()


def test_the_start_values_are_listed_with_their_unit_for_the_start_up_block() -> None:
    client = _create_client_with_spy(fmu_instance=SpyFMUInstance(), is_initialized=False, start_value_texts={"mass.s": "1.25"})

    assert client._start_values_for_start_up() == ["mass.s = 1.25 m"]  # noqa: SLF001
    client.on_app_shutdown()
