from pathlib import Path
from typing import override

import pytest
import sys

from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_test_common.resources.resource_utils import config_parser_for_resource
from integration_tests.clients.base.client_base_test_case import ClientBaseTest

_INPUT_INTERFACES_TO_FACTOR = {"Float64_continuous_input": 1.0, "Float64_discrete_input": 10.0}


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on Windows")
class TestFMU2ClientBase(ClientBaseTest):
    """Runs the 'Feedthrough' Reference FMU (FMI 2.0), which sets every output to the value of its input."""

    @override
    def create_client(self, config_override: ClientConfigOverride) -> SimulatorClient:
        return FMU2Client.create(
            config_parser=config_parser_for_resource("integration/models/fmu2/configs/feedthrough.ini"),
            config_override=config_override,
        )

    @override
    def input_value_generator(self, name: str, passed_seconds: float) -> InterfaceValue:
        return _INPUT_INTERFACES_TO_FACTOR[name] * passed_seconds

    @override
    def assert_outputs(self, passed_seconds: float, outputs: dict[str, InterfaceValue]) -> None:
        assert outputs == {
            "Float64_continuous_output": self.input_value_generator("Float64_continuous_input", passed_seconds),
            "Float64_discrete_output": self.input_value_generator("Float64_discrete_input", passed_seconds),
        }

    @override
    def assert_resources_released(self, client: SimulatorClient) -> None:
        assert isinstance(client, FMU2Client)
        assert not Path(client._simulator_config.unzip_dir()).exists()  # noqa: SLF001
