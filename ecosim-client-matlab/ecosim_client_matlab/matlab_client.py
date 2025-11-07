from typing_extensions import override

from ecosim_client_matlab.matlab_config import MatlabConfig
from ecosim_client_matlab.matlab_simulator import MatlabSimulator
from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.client.client import Client
from ecosim_common.client.renderer.simulation_renderer_service import SimulationRendererService
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.simulation.interface_id import InterfaceId


class MatlabClient(Client):

    def __init__(
        self,
        config_parser: ConfigParser,
        config_overrides: ClientConfigOverride,
    ):
        super().__init__(SimpleClientConfig.of_config_parser(config_parser, config_overrides))
        self._simulator: MatlabSimulator = MatlabSimulator(
            execution_config=self._execution_config,
            client_config=self._client_config,
            matlab_config=MatlabConfig(config_parser),
        )
        self._is_finished = False

    @override
    def on_app_shutdown(self) -> None:
        super().on_app_shutdown()

    @override
    def on_simulation_start(self) -> ClientSimStepData:
        self._simulator.initialize(start_time=0.0)
        return self._simulator.server_used_output_values()

    @override
    def on_simulation_step(
        self,
        received_inputs: dict[InterfaceId, InterfaceValueType],
        step_size_in_seconds: float,
    ) -> ClientSimStepData:
        self._simulator.do_step(
            input_values=received_inputs,
            step_size_in_seconds=step_size_in_seconds,
        )
        return self._simulator.server_used_output_values()

    @override
    def on_simulation_stop(self) -> None:
        pass

    @override
    def image_renderer_service(self) -> SimulationRendererService:
        # TODO
        Client.logger.warning("Image rendering method not implemented, yet.")
        return None  # type: ignore # TODO
