from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, override

from ecosim_common.client.client import Client
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue, ProtocolInterfaceValue
from ecosim_common.simulation.interface_id import InterfaceId


@dataclass
class SimulatorClient(Client, ABC):
    """
    A basic template that assumes that 'input' and 'output' values are set 'somewhere' and can be read from 'somewhere'.

    On each step, all received inputs are set first, then the model advances by one step, and finally the outputs
    the server uses are read. The model is initialized once at simulation start and cleared once at app shutdown.
    For each of the steps described above, there are callbacks for the concrete classes to implement.

    Please note, that the __post_init__ method is essential. If you overwrite it in a subclass, you need to call
    the parent's __post_init__ method as well.
    """

    _current_simulation_time: float = field(default=0.0)
    _is_initialized: bool = field(default=False)
    _is_cleared: bool = field(default=False)

    def __post_init__(self) -> None:
        super().__post_init__()

    def _initialize_model(self, start_time: float = 0.0) -> None:
        if self._is_initialized:
            self.logger.warning("Already initialized, skipping initialization.")
            return
        self.logger.info("Initializing with start_time %s", start_time)
        self._current_simulation_time = start_time
        self._on_initialize_model(start_time)
        self._is_initialized = True
        self.logger.debug("Initializing... finished.")

    @override
    def on_simulation_start(self) -> ClientSimStepData:
        """
        In theory, we can have a start_time != 0.0. The current protocol does not support it, but the foundation is already laid.
        To implement it, we need to adapt the SIMULATION_START message to contain a corresponding parameter. We also need to
        check all clients, if they handle the start_time correctly (e.g. the MatLab and Pyro clients currently ignore it).
        """
        self._initialize_model(start_time=0.0)
        return self._server_used_output_values()

    @override
    def on_simulation_step(
        self,
        received_inputs: Dict[InterfaceId, InterfaceValue],
        step_size_in_seconds: float,
    ) -> ClientSimStepData:
        self._do_model_step(
            input_values=received_inputs,
            step_size_in_seconds=step_size_in_seconds,
        )
        return self._server_used_output_values()

    @override
    def on_simulation_stop(self) -> None:
        pass

    @abstractmethod
    def _on_initialize_model(self, start_time: float) -> None:
        pass

    def _server_used_output_values(self) -> ClientSimStepData:
        return ClientSimStepData.of_protocol_interface_values(
            [
                ProtocolInterfaceValue(
                    name=interface_name,
                    value=self._get_model_output(interface_name),
                )
                for interface_name in self._execution_config.server_used_outputs()
            ],
        )

    @abstractmethod
    def _get_model_output(
        self,
        name: str,
    ) -> InterfaceValue:
        pass

    @abstractmethod
    def _set_input_float(
        self,
        name: str,
        value: float | None,
    ) -> None:
        pass

    @abstractmethod
    def _set_input_float_matrix(
        self,
        name: str,
        value: FloatMatrix,
    ) -> None:
        pass

    @abstractmethod
    def _on_do_step(
        self,
        step_size_in_seconds: float,
    ) -> None:
        """
        The callback method to do the actual work. At this point, all setters regarding the input are already called.
        """
        pass

    @abstractmethod
    def _on_clear_simulator(self) -> None:
        pass

    def _do_model_step(
        self,
        input_values: dict[InterfaceId, InterfaceValue],
        step_size_in_seconds: float,
    ) -> None:
        for interface_id, value in input_values.items():
            if isinstance(value, list):
                self._set_input_float_matrix(interface_id, value)
            else:
                self._set_input_float(interface_id, value)
        self.logger.info(
            "Executing next step (current_simulation_time=%s | step_size=%s)...",
            self._current_simulation_time,
            step_size_in_seconds,
        )
        self._on_do_step(
            step_size_in_seconds=step_size_in_seconds,
        )
        self._current_simulation_time += step_size_in_seconds
        self.logger.debug("Executing next step finished (current_simulation_time=%s).", self._current_simulation_time)

    @override
    def on_app_shutdown(self) -> None:
        super().on_app_shutdown()
        if not self._is_cleared:
            self._clear_simulator()

    def _clear_simulator(self) -> None:
        if self._is_cleared:
            self.logger.warning("Simulator already cleared, skipping clearing.")
            return
        self.logger.info("Clearing simulator...")
        self._is_cleared = True
        self._on_clear_simulator()
        self.logger.debug("Clearing simulator...done.")
