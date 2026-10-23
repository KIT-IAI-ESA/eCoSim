import threading
from pathlib import Path
from typing import Any, Generator, override

import Pyro5.api
import pytest
from ecosim_client_pyro5.pyro_client import PyroClient
from ecosim_common.client.config.client_config import ClientConfigOverride
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType

from integration_tests.clients.base.client_base_test_case import ClientBaseTest
from integration_tests.test_data.write_ini import write_client_ini, write_fmc

_OBJECT_NAME = "pyro5_test_model"


@Pyro5.api.expose
class PyroTestModel:
    def initialize(self) -> dict[str, float]:
        return {"y": 0.0}

    def do_step(self, inputs: dict[str, float]) -> dict[str, float]:
        return {"y": 2 * inputs["u"]}

    def clear(self) -> None:
        pass


class TestPyro5ClientBase(ClientBaseTest):
    _daemon_port: int
    _config_directory: Path

    @pytest.fixture(autouse=True)
    def _pyro_daemon(self, tmp_path: Path) -> Generator[None, Any, None]:
        daemon = Pyro5.api.Daemon(host="localhost", port=0)
        daemon.register(PyroTestModel(), objectId=_OBJECT_NAME)
        threading.Thread(target=daemon.requestLoop, daemon=True).start()
        self._daemon_port = daemon.sock.getsockname()[1]
        self._config_directory = tmp_path
        yield None
        daemon.shutdown()

    @override
    def create_client(self, config_override: ClientConfigOverride) -> SimulatorClient:
        pyro_section = {"pyro_host": "localhost", "pyro_port": str(self._daemon_port), "pyro_object_name": _OBJECT_NAME}
        fmc_file = write_fmc(self._config_directory, inputs=["u"], outputs=["y"])
        config_parser = write_client_ini(self._config_directory, "pyro5", "pyro5_model", fmc_file, {"pyro": pyro_section})
        return PyroClient.of(config_parser=config_parser, config_override=config_override)

    @override
    def assert_outputs(self, passed_seconds: float, outputs: dict[str, InterfaceValueType]) -> None:
        assert outputs == {"y": 2 * passed_seconds}

    @override
    def input_value_generator(self, name: str, passed_seconds: float) -> InterfaceValueType:
        return passed_seconds
