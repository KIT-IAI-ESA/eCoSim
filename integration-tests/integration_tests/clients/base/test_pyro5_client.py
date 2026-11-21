import threading
from pathlib import Path
from typing import Any, Generator, override

import Pyro5.api
import pytest

from ecosim_client_pyro5.pyro_client import PyroClient
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import InterfaceValue
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.port_utils import get_free_port
from integration_tests.clients.base.client_base_test_case import ClientBaseTest
from integration_tests.test_data.write_ini import write_client_ini, write_fmc

_OBJECT_NAME = "pyro5_test_model"


@Pyro5.api.expose
class PyroTestModel:
    def __init__(self) -> None:
        self.holds_state = False
        self.start_outputs: dict[str, float] = {"y": 0.0}
        self.clear_fails = False
        self.do_step_closes_the_connection = False

    def initialize(self) -> dict[str, float]:
        self.holds_state = True
        return self.start_outputs

    def do_step(self, inputs: dict[str, float]) -> dict[str, float]:
        if self.do_step_closes_the_connection:
            Pyro5.api.current_context.client.close()
        return {"y": 2 * inputs["u"]}

    def clear(self) -> None:
        if self.clear_fails:
            raise RuntimeError("the model could not clean up")
        self.holds_state = False


class TestPyro5ClientBase(ClientBaseTest):
    _pyro_port: int
    _config_directory: Path
    _model: PyroTestModel
    _daemon: Pyro5.api.Daemon

    @pytest.fixture(autouse=True)
    def _pyro_daemon(self, tmp_path: Path) -> Generator[None, Any, None]:
        self._daemon = Pyro5.api.Daemon(host="localhost", port=0)
        self._model = PyroTestModel()
        self._daemon.register(self._model, objectId=_OBJECT_NAME)
        threading.Thread(target=self._daemon.requestLoop, daemon=True).start()
        self._pyro_port = self._daemon.sock.getsockname()[1]
        self._config_directory = tmp_path
        yield None
        self._daemon.shutdown()

    @override
    def create_client(self, config_override: ClientConfigOverride) -> SimulatorClient:
        pyro_section = {"pyro_host": "localhost", "pyro_port": str(self._pyro_port), "pyro_object_name": _OBJECT_NAME}
        fmc_file = write_fmc(self._config_directory, inputs=["u"], outputs=["y"])
        config_parser = ConfigParser(
            path=write_client_ini(self._config_directory, "pyro5", "pyro5_model", fmc_file, {"pyro": pyro_section}),
        )
        return PyroClient.of(config_parser=config_parser, config_override=config_override)

    @override
    def assert_outputs(self, passed_seconds: float, outputs: dict[str, InterfaceValue]) -> None:
        assert outputs == {"y": 2 * passed_seconds}

    @override
    def input_value_generator(self, name: str, passed_seconds: float) -> InterfaceValue:
        return passed_seconds

    @override
    def assert_resources_released(self, client: SimulatorClient) -> None:
        assert not self._model.holds_state

    def test_converts_integer_and_boolean_outputs_to_float(self) -> None:
        self._model.start_outputs = {"count": 3, "is_on": True}
        client = self.create_client(config_override=ClientConfigOverride())
        client.on_simulation_start()

        outputs = [client._get_model_output(name) for name in ("count", "is_on")]  # noqa: SLF001

        assert outputs == [3.0, 1.0]
        assert [type(output) for output in outputs] == [float, float]

    def test_a_failing_model_call_logs_the_line_in_the_model(self, caplog: pytest.LogCaptureFixture) -> None:
        self._model.clear_fails = True
        client = self.create_client(config_override=ClientConfigOverride())
        client.on_simulation_start()

        with pytest.raises(RuntimeError, match="the model could not clean up"):
            client.on_app_shutdown()

        assert 'raise RuntimeError("the model could not clean up")' in caplog.text

    def test_the_error_names_the_ini_keys_when_nothing_listens_for_the_pyro5_object(self) -> None:
        self._pyro_port = get_free_port()
        client = self.create_client(config_override=ClientConfigOverride())

        with pytest.raises(ConnectionError) as error:
            client.on_simulation_start()

        assert str(error.value) == (
            f"{self._config_directory / 'client.ini'}: nothing listens on pyro_host localhost and pyro_port {self._pyro_port}. "
            + "Start the Pyro5 object before the run. If it runs already, set pyro_host and pyro_port to the address it listens on."
        )

    def test_the_error_names_the_ini_keys_when_the_pyro5_object_closes_the_connection(self) -> None:
        self._model.do_step_closes_the_connection = True
        client = self.create_client(config_override=ClientConfigOverride())
        client.on_simulation_start()

        with pytest.raises(ConnectionError) as error:
            client.on_simulation_step(received_inputs={"u": 1.0}, step_size_in_seconds=1.0)

        assert str(error.value) == (
            f"{self._config_directory / 'client.ini'}: lost the connection to the Pyro5 object on pyro_host localhost "
            + f"and pyro_port {self._pyro_port}. The Pyro5 object has to run until the simulation ends."
        )

    def test_a_pyro5_object_that_is_gone_at_the_end_is_not_cleared(self, caplog: pytest.LogCaptureFixture) -> None:
        self._model.do_step_closes_the_connection = True
        client = self.create_client(config_override=ClientConfigOverride())
        client.on_simulation_start()
        with pytest.raises(ConnectionError):
            client.on_simulation_step(received_inputs={"u": 1.0}, step_size_in_seconds=1.0)
        self._daemon.shutdown()

        client.on_app_shutdown()

        assert f"pyro_port {self._pyro_port} is not reachable, so it was not cleared." in caplog.text
