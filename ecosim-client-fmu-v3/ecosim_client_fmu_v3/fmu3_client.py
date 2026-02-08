import os
from typing import Dict

from typing_extensions import override

from ecosim_client_fmu_v3.fmu3_config import FMU3Config
from ecosim_client_fmu_v3.fmu3_simulator import FMU3Simulator
from ecosim_common.client.client import Client
from ecosim_common.client.config.client_config import ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.renderer.pre_rendered_images_service import PreRenderedImageService, \
    PreRenderedImageServiceConfig
from ecosim_common.client.renderer.simulation_renderer_service import SimulationRendererService
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import InterfaceValueType
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.simulation.interface_id import InterfaceId


class FMU3Client(Client):

    def __init__(
        self,
        config_parser: ConfigParser,
        config_override: ClientConfigOverride | None = None,
        dask_connector: bool = False,
    ):
        super().__init__(SimpleClientConfig.of_config_parser(config_parser, config_override), dask_connector)
        self._config_path = config_parser.config_file
        self._fmu_config = FMU3Config.of(config_parser)
        self._simulator: FMU3Simulator | None = None
        self._is_finished = False

    @override
    def on_app_shutdown(self) -> None:
        super().on_app_shutdown()
        if self._simulator is not None:
            self._simulator.on_app_shutdown()

    @override
    def on_simulation_start(self) -> ClientSimStepData:
        self._simulator = FMU3Simulator.of(
            simulator_name=self._client_config.simulator_config().simulator_name,
            fmu_config=self._fmu_config,
            execution_config=self._execution_config,
        )
        self._simulator.initialize(start_time=0.0)
        return self._simulator.server_used_output_values()

    @override
    def on_simulation_step(
        self,
        received_inputs: Dict[InterfaceId, InterfaceValueType],
        step_size_in_seconds: float,
    ) -> ClientSimStepData:
        if self._simulator is None:
            raise RuntimeError('Simulation has not been started')
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
        pre_rendered_images_dir = os.path.dirname(self._config_path) + "/rendered_images"
        Client.logger.debug(f"Pre-rendered images dir: '{pre_rendered_images_dir}'.")
        return PreRenderedImageService(
            PreRenderedImageServiceConfig(
                image_dir=pre_rendered_images_dir,
            ),
        )
