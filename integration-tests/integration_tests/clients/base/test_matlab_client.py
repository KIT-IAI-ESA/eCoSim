import logging
import re
import sys
from pathlib import Path
from typing import Callable, override

import pytest

from ecosim_client_matlab.matlab_client import MatlabClient
from ecosim_client_matlab.matlab_config import MatlabConfig
from ecosim_client_matlab.matlab_engine import MatlabEngine, start_matlab
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.config_parser import ConfigParser
from integration_tests.clients.base.base_simulation import BaseSimulation
from integration_tests.clients.base.client_base_test_case import ClientBaseTest
from integration_tests.clients.base.fake_matlab import FakeMatlab, FakeMatlabEngine, FakeMatlabExecutionError
from integration_tests.test_data.write_ini import write_client_ini, write_fmc


def _client_log_entries(caplog: pytest.LogCaptureFixture) -> set[tuple[int, str]]:
    return {(record.levelno, record.getMessage()) for record in caplog.records if record.name == MatlabClient.__name__}


class TestMatlabClientBase(ClientBaseTest):
    _config_directory: Path
    _fake_matlab: FakeMatlab

    @pytest.fixture(autouse=True)
    def _config_in(self, tmp_path: Path) -> None:
        self._config_directory = tmp_path
        self._fake_matlab = FakeMatlab()
        for script_name in MatlabConfig.SCRIPT_NAMES:
            (tmp_path / script_name).write_text("")

    @override
    def create_client(self, config_override: ClientConfigOverride) -> SimulatorClient:
        return self._create_matlab_client(config_override=config_override, start_matlab=self._fake_matlab.start_matlab)

    def _create_matlab_client(self, config_override: ClientConfigOverride, start_matlab: Callable[[], MatlabEngine]) -> MatlabClient:
        matlab_section = {"scriptfolder": str(self._config_directory)}
        fmc_file = write_fmc(self._config_directory, inputs=["u"], outputs=["y", "time"])
        config_parser = ConfigParser(
            path=write_client_ini(self._config_directory, "matlab", "matlab_model", fmc_file, {"matlab": matlab_section}),
        )
        return MatlabClient.of(config_parser=config_parser, config_overrides=config_override, start_matlab=start_matlab)

    @override
    def assert_outputs(self, passed_seconds: float, outputs: dict[str, InterfaceValue]) -> None:
        # 'time' is the simulation time at the start of the step
        assert outputs == {"y": 2 * passed_seconds, "time": passed_seconds - self.STEP_SIZE_IN_SECONDS}

    @override
    def input_value_generator(self, name: str, passed_seconds: float) -> InterfaceValue:
        return passed_seconds

    @override
    def assert_resources_released(self, client: SimulatorClient) -> None:
        assert isinstance(client, MatlabClient)
        assert client._matlab_engine_or_none is None  # noqa: SLF001
        assert all(engine.is_shut_down for engine in self._fake_matlab.started)

    def test_starts_one_engine_and_shuts_it_down(self, simulation: BaseSimulation) -> None:
        simulation.client.on_app_shutdown()
        assert [engine.is_shut_down for engine in self._fake_matlab.started] == [True]

    def test_shuts_the_engine_down_when_finishing_fails(self) -> None:
        fake_matlab = FakeMatlab(fails_on_finishing=True)
        client = self._create_matlab_client(config_override=ClientConfigOverride(), start_matlab=fake_matlab.start_matlab)
        client.on_simulation_start()

        with pytest.raises(FakeMatlabExecutionError):
            client.on_app_shutdown()

        assert [engine.is_shut_down for engine in fake_matlab.started] == [True]

    def test_forwards_the_output_of_a_step_to_the_logger(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.INFO, logger=MatlabClient.__name__)
        client = self._create_matlab_client(config_override=ClientConfigOverride(), start_matlab=self._fake_matlab.start_matlab)
        client.on_simulation_start()

        client.on_simulation_step(received_inputs={"u": 1.0}, step_size_in_seconds=self.STEP_SIZE_IN_SECONDS)

        assert {(logging.INFO, FakeMatlabEngine.STEP_OUTPUT), (logging.WARNING, FakeMatlabEngine.STEP_ERROR_OUTPUT)} <= _client_log_entries(caplog)

    def test_forwards_the_error_output_of_a_failing_script_to_the_logger(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.WARNING, logger=MatlabClient.__name__)
        fake_matlab = FakeMatlab(fails_on_finishing=True)
        client = self._create_matlab_client(config_override=ClientConfigOverride(), start_matlab=fake_matlab.start_matlab)
        client.on_simulation_start()

        with pytest.raises(FakeMatlabExecutionError):
            client.on_app_shutdown()

        assert (logging.WARNING, FakeMatlabEngine.FINISHING_ERROR_OUTPUT) in _client_log_entries(caplog)

    def test_converts_integer_and_boolean_outputs_to_float(self) -> None:
        client = self._create_matlab_client(config_override=ClientConfigOverride(), start_matlab=self._fake_matlab.start_matlab)
        client.on_simulation_start()
        self._fake_matlab.started[0].workspace.update(count=3, is_on=True)

        outputs = [client._get_model_output(name) for name in ("count", "is_on")]  # noqa: SLF001

        assert outputs == [3.0, 1.0]
        assert [type(output) for output in outputs] == [float, float]

    def test_starting_the_model_without_the_matlab_engine_asks_to_install_it(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 'None' in 'sys.modules' fails the import even where Matlab is installed
        monkeypatch.setitem(sys.modules, "matlab.engine", None)
        client = self._create_matlab_client(config_override=ClientConfigOverride(), start_matlab=start_matlab)

        with pytest.raises(ImportError, match=re.escape("uv sync --extra R2024b")):
            client.on_simulation_start()
