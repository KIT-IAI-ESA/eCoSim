from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_client_fmu_v3.fmu3_simulator_config import FMU3SimulatorConfig
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.simulations.state_space_simulation_data import StateSpaceSimulationData
from ecosim_test_common.test_data.generate_client_config import generate_mocked_client_config

from tests.tech.resource_utils import resource_path

_FMU_FILE = resource_path() / "test_fmus/StateSpace.fmu"


@skip_unless_fmpy_loads(_FMU_FILE)
@pytest.mark.parametrize("fixed_size_output", [False, True], ids=["output size from a parameter", "fixed output size"])
def test_with_matrix_inputs(tmp_path: Path, fixed_size_output: bool) -> None:
    fmu_file = (
        StateSpaceSimulationData.fmu_file_with_fixed_dimension(directory=tmp_path, value_reference=3, start=3) if fixed_size_output else _FMU_FILE
    )
    simulator_config = FMU3SimulatorConfig.of(
        simulator_name="test_simulator",
        fmu_config=FMUBaseConfig(fmu_file=fmu_file),
        input_names=["u"],
        output_names=["y"],
    )
    client = FMU3Client(
        _client_config=generate_mocked_client_config(),
        _channel_or_none=MagicMock(spec=ESPChannel),
        _simulation_config=simulator_config,
        _fmu_instance=simulator_config.create_fmu_instance(),
    )
    client._initialize_model()  # noqa: SLF001

    client._do_model_step(input_values={"u": [111.0, 222.0, 333.0]}, step_size_in_seconds=1)  # noqa: SLF001
    assert client._get_model_output("y") == [301.57855647818417, 603.1571129563683, 904.7356694345515]  # noqa: SLF001

    client._do_model_step(input_values={"u": [222.0, 444.0, 666.0]}, step_size_in_seconds=1)  # noqa: SLF001
    assert client._get_model_output("y") == [1120.9445540229174, 2241.8891080458347, 3362.8336620687433]  # noqa: SLF001
    client.on_app_shutdown()
