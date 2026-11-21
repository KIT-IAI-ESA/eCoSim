from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import override

import Pyro5.api
import Pyro5.errors
from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_common.config.config_parser import ConfigParser

from ecosim_client_pyro5.pyro_config import PyroConfig


@dataclass(kw_only=True)
class PyroClient(SimulatorClient):
    _pyro_config: PyroConfig
    _simulation_object: Pyro5.api.Proxy
    _input_dict: dict[str, InterfaceValue] = field(default_factory=dict)
    _output_dict: dict[str, float] = field(default_factory=dict)

    @staticmethod
    def of(
        config_parser: ConfigParser,
        config_override: ClientConfigOverride,
    ) -> PyroClient:
        client_config = SimpleClientConfig.of_config_parser(config_parser, config_override)
        pyro_config = PyroConfig.of(config_parser=config_parser)
        simulation_object = Pyro5.api.Proxy(f"PYRO:{pyro_config.object_name}@{pyro_config.host}:{pyro_config.port}")
        return PyroClient(
            _client_config=client_config,
            _pyro_config=pyro_config,
            _simulation_object=simulation_object,
        )

    @override
    def _on_initialize_model(self) -> None:
        self._simulation_object._pyroClaimOwnership()
        with self._log_model_traceback_on_error(method_name="initialize"), self._name_the_ini_keys_on_connection_error():
            self._output_dict = self._simulation_object.initialize()

    @override
    def _set_input_float(
        self,
        name: str,
        value: float | None,
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._input_dict[name] = value

    @override
    def _set_input_float_matrix(
        self,
        name: str,
        value: FloatMatrix,
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._input_dict[name] = value

    @override
    def _get_model_output(self, name: str) -> InterfaceValue:
        value = self._output_dict[name]
        if isinstance(value, (int, bool)):
            return float(value)
        return value

    @override
    def _before_handle_message(
        self,
        message: ESPChannelMessage,
    ) -> None:
        # noinspection protected-member
        self._simulation_object._pyroClaimOwnership()

    @override
    def _on_do_step(
        self,
        step_size_in_seconds: float,
    ) -> None:
        with self._log_model_traceback_on_error(method_name="do_step"), self._name_the_ini_keys_on_connection_error():
            self._output_dict = self._simulation_object.do_step(self._input_dict)

    @override
    def _on_clear_simulator(self) -> None:
        if not self._is_initialized:
            self.logger.debug("Remote model was never initialized, nothing to clear.")
            return
        self._simulation_object._pyroClaimOwnership()
        self.logger.debug("        ->> terminating instance...")
        try:
            with self._log_model_traceback_on_error(method_name="clear"):
                self._simulation_object.clear()
        except Pyro5.errors.CommunicationError:
            self.logger.warning(
                "%s: the Pyro5 object on pyro_host %s and pyro_port %s is not reachable, so it was not cleared.",
                self._pyro_config.config_file,
                self._pyro_config.host,
                self._pyro_config.port,
            )

    @contextmanager
    def _log_model_traceback_on_error(
        self,
        method_name: str,
    ) -> Iterator[None]:
        try:
            yield
        except Exception as error:
            # the local traceback only shows Pyro, the line in the model comes with the error
            model_traceback = getattr(error, "_pyroTraceback", None)
            if model_traceback:
                self.logger.error("The Pyro model failed in %s():\n%s", method_name, "".join(model_traceback))
            raise

    @contextmanager
    def _name_the_ini_keys_on_connection_error(self) -> Iterator[None]:
        config_file = self._pyro_config.config_file
        address = f"pyro_host {self._pyro_config.host} and pyro_port {self._pyro_config.port}"
        try:
            yield
        except Pyro5.errors.ConnectionClosedError as error:
            raise ConnectionError(
                f"{config_file}: lost the connection to the Pyro5 object on {address}. The Pyro5 object has to run until the simulation ends.",
            ) from error
        except Pyro5.errors.CommunicationError as error:
            # only a failed connect has an OSError behind it, a wrong pyro_object_name does not
            if not isinstance(error.__cause__, OSError):
                raise
            raise ConnectionError(
                f"{config_file}: nothing listens on {address}. Start the Pyro5 object before the run. "
                + "If it runs already, set pyro_host and pyro_port to the address it listens on.",
            ) from error
