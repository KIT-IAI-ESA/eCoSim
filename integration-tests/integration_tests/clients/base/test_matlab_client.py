from pathlib import Path
from typing import override

import pytest

from ecosim_client_matlab.matlab_client import MatlabClient
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.config_parser import ConfigParser
from integration_tests.clients.base.base_simulation import BaseSimulation
from integration_tests.clients.base.client_base_test_case import ClientBaseTest
from integration_tests.clients.base.fake_matlab import FakeMatlab
from integration_tests.test_data.write_ini import write_client_ini, write_fmc


class TestMatlabClientBase(ClientBaseTest):
    _config_directory: Path

    @pytest.fixture(autouse=True)
    def _config_in(self, tmp_path: Path, fake_matlab: FakeMatlab) -> None:
        # requesting 'fake_matlab' here puts the fake in place for every test of this class
        self._config_directory = tmp_path

    @override
    def create_client(self, config_override: ClientConfigOverride) -> SimulatorClient:
        matlab_section = {"scriptfolder": str(self._config_directory)}
        fmc_file = write_fmc(self._config_directory, inputs=["u"], outputs=["y", "time"])
        config_parser = ConfigParser(
            path=write_client_ini(self._config_directory, "matlab", "matlab_model", fmc_file, {"matlab": matlab_section}),
        )
        return MatlabClient.of(config_parser=config_parser, config_overrides=config_override)

    @override
    def assert_outputs(self, passed_seconds: float, outputs: dict[str, InterfaceValue]) -> None:
        # 'time' is the simulation time at the start of the step
        assert outputs == {"y": 2 * passed_seconds, "time": passed_seconds - self.STEP_SIZE_IN_SECONDS}

    @override
    def input_value_generator(self, name: str, passed_seconds: float) -> InterfaceValue:
        return passed_seconds

    def test_starts_one_engine_and_shuts_it_down(self, simulation: BaseSimulation, fake_matlab: FakeMatlab) -> None:
        simulation.client.on_app_shutdown()
        assert [engine.is_shut_down for engine in fake_matlab.started] == [True]
