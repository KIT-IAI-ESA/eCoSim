from typing import Any
from unittest.mock import MagicMock

import pytest
from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import resource_path
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config

_FMU_FILE = resource_path() / "fmu_v2" / "test_fmus" / "Sub1_Linux.fmu"


def _create_client() -> FMU2Client:
    fmu_config = FMUBaseConfig(fmu_file=_FMU_FILE)
    simulator_config = FMU2SimulatorConfig.of(simulator_name="test_simulator", fmu_config=fmu_config)
    return FMU2Client(
        _client_config=generate_mocked_client_config(),
        _channel_or_none=MagicMock(spec=ESPChannel),
        _simulator_config=simulator_config,
        _fmu_instance=simulator_config.create_fmu2_instance(),
    )


def _read_input(client: FMU2Client, name: str) -> list[float]:
    fmu_instance = client._fmu_instance  # noqa: SLF001
    simulator_config = client._simulator_config  # noqa: SLF001
    return fmu_instance.getReal([simulator_config.input_value_references(name)])


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
