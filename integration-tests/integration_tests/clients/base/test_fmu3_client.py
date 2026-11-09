from pathlib import Path
from typing import override

from ecosim_client_fmu_v3.fmu3_client import FMU3Client
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import config_parser_for_resource, fmu3_model_path
from integration_tests.clients.base.client_base_test_case import ClientBaseTest
from integration_tests.fmu.fmu3_state_space_model import state_space_outputs

_INPUT_FACTORS = (1.0, 1_000.0, 100_000.0)


@skip_unless_fmpy_loads(fmu3_model_path())
class TestFMU3ClientBase(ClientBaseTest):
    @override
    def create_client(self, config_override: ClientConfigOverride) -> SimulatorClient:
        return FMU3Client.of(
            config_parser=config_parser_for_resource("integration/models/fmu3/configs/state_space.ini"),
            config_override=config_override,
        )

    @override
    def input_value_generator(self, name: str, passed_seconds: float) -> InterfaceValue:
        return [factor * passed_seconds for factor in _INPUT_FACTORS]

    @override
    def assert_outputs(self, passed_seconds: float, outputs: dict[str, InterfaceValue]) -> None:
        assert outputs == {"y": state_space_outputs(int(passed_seconds), _INPUT_FACTORS)}

    @override
    def assert_resources_released(self, client: SimulatorClient) -> None:
        assert isinstance(client, FMU3Client)
        assert not Path(client._simulation_config.unzip_dir).exists()  # noqa: SLF001
