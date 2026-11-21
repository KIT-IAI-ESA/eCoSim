from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from typing import override

import fmpy
from ecosim_common.client.config.client_config import ClientConfig, ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.client.renderer.pre_rendered_images_service import PreRenderedImageService
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.one_line_errors import one_line_message
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig

from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig


@dataclass(kw_only=True)
class FMU2Client(SimulatorClient):
    _simulator_config: FMU2SimulatorConfig = field()
    _fmu_instance: fmpy.fmi2.FMU2Slave = field()

    @staticmethod
    def create(
        config_parser: ConfigParser,
        config_override: ClientConfigOverride,
    ) -> FMU2Client:
        client_config: ClientConfig = SimpleClientConfig.of_config_parser(config_parser, config_override)
        image_renderer_service = PreRenderedImageService.of_config_path(config_parser.config_file)
        fmu_config = FMUBaseConfig.of_config_parser(config_parser)
        execution_config = ExecutionConfig()
        simulator_config = FMU2SimulatorConfig.of(
            simulator_name=client_config.simulator_config().simulator_name,
            fmu_config=fmu_config,
            input_names=client_config.interfaces_config().input_interface_names(),
            output_names=client_config.interfaces_config().output_interface_names(),
        )
        return FMU2Client(
            _client_config=client_config,
            _image_renderer_service=image_renderer_service,
            _execution_config=execution_config,
            _simulator_config=simulator_config,
            _fmu_instance=simulator_config.create_fmu2_instance(),
        )

    @override
    def _on_initialize_model(self) -> None:
        self._fmu_instance.instantiate()
        self._fmu_instance.setupExperiment()
        self._simulator_config.start_values().set_on(self._fmu_instance)
        self._fmu_instance.enterInitializationMode()
        self._fmu_instance.exitInitializationMode()

    @override
    def _start_values_for_start_up(self) -> list[str]:
        return self._simulator_config.start_values().as_lines()

    @override
    def _reason_the_model_cannot_run(self, server_interface_settings: ServerInterfaceSettings) -> str | None:
        return self._simulator_config.reason_the_model_cannot_run(server_interface_settings=server_interface_settings)

    @override
    def _set_input_float(
        self,
        name: str,
        value: float | None,  # noqa: F821
    ) -> None:
        self.logger.debug("Setting float input %s to %s", name, value)
        self._fmu_instance.setReal([self._simulator_config.input_value_references(name)], [value])

    @override
    def _get_model_output(
        self,
        name: str,
    ) -> InterfaceValue:
        value: float = self._fmu_instance.getReal([self._simulator_config.output_value_references(name)])[0]
        self.logger.debug("Getting float output %s: %s", name, value)
        return value

    @override
    def _on_clear_simulator(self) -> None:
        try:
            # the FMU is extracted on creation, but only instantiated when the simulation starts
            if self._is_initialized:
                self.logger.debug("        ->> terminating instance...")
                self._fmu_instance.terminate()
        finally:
            self._free_fmu_instance()
            self.logger.debug("        ->> removing extracted files...")
            shutil.rmtree(self._simulator_config.unzip_dir(), ignore_errors=True)

    def _free_fmu_instance(self) -> None:
        self.logger.debug("        ->> freeing instance...")
        try:
            self._fmu_instance.freeInstance()
        except Exception as error:
            self.logger.exception("Freeing the FMU instance failed: %s", one_line_message(error=error))

    @override
    def _set_input_float_matrix(
        self,
        name: str,
        value: FloatMatrix,
    ) -> None:
        raise TypeError("FMUv2 cannot handle matrix types.")

    @override
    def _on_do_step(
        self,
        step_size_in_seconds: float,
    ) -> None:
        self._fmu_instance.doStep(
            currentCommunicationPoint=self._current_simulation_time,
            communicationStepSize=step_size_in_seconds,
        )
