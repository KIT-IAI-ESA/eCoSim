from pathlib import Path
from typing import override

import pytest

from ecosim_client_python.python_client import PythonClient
from ecosim_client_python.python_model import PythonModel
from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.config_parser import ConfigParser
from ecosim_test_common.test_data.python_models import DoublingModel
from integration_tests.clients.base.client_base_test_case import ClientBaseTest
from integration_tests.test_data.write_ini import write_client_ini, write_fmc


class TestPythonClientBase(ClientBaseTest):
    _config_directory: Path
    _model: DoublingModel

    @pytest.fixture(autouse=True)
    def _python_model(self, tmp_path: Path) -> None:
        self._model = DoublingModel()
        self._config_directory = tmp_path

    @override
    def create_client(self, config_override: ClientConfigOverride) -> SimulatorClient:
        fmc_file = write_fmc(directory=self._config_directory, inputs=["u"], outputs=["y"])
        ini_file = write_client_ini(directory=self._config_directory, client_type="python", model_name="python_model", fmc_file=fmc_file)
        # the model object of the test, so assert_resources_released can look at it
        return PythonClient(
            _client_config=SimpleClientConfig.of_config_parser(config_parser=ConfigParser(path=ini_file), config_override=config_override),
            _model=PythonModel.of_object(model=self._model, model_reference="DoublingModel"),
        )

    @override
    def assert_outputs(self, passed_seconds: float, outputs: dict[str, InterfaceValue]) -> None:
        assert outputs == {"y": 2 * passed_seconds}

    @override
    def input_value_generator(self, name: str, passed_seconds: float) -> InterfaceValue:
        return passed_seconds

    @override
    def assert_resources_released(self, client: SimulatorClient) -> None:
        assert not self._model.holds_state
