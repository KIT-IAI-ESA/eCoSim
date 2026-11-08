from __future__ import annotations

import shutil
import weakref
from dataclasses import dataclass, field
from typing import override

import fmpy
from ecosim_common.client.config.client_config import ClientConfig, ClientConfigOverride, SimpleClientConfig
from ecosim_common.client.config.execution_config import ExecutionConfig
from ecosim_common.client.renderer.pre_rendered_images_service import PreRenderedImageService
from ecosim_common.client.simulator_client import SimulatorClient
from ecosim_common.communication.data.protocol_interface_value import FloatMatrix, InterfaceValue
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig

from ecosim_client_fmu_v2.fmu2_simulator_config import FMU2SimulatorConfig


@dataclass(kw_only=True)
class FMU2Client(SimulatorClient):
    _simulator_config: FMU2SimulatorConfig = field()
    _fmu_instance: fmpy.fmi2.FMU2Slave = field()
    # also called when the process ends, for a client that is never cleared
    _remove_extracted_files: weakref.finalize[..., FMU2Client] = field(init=False)

    @override
    def __post_init__(self) -> None:
        # set first: registering the client clears it at once if a shutdown already started
        self._remove_extracted_files = weakref.finalize(self, shutil.rmtree, self._simulator_config.unzip_dir())
        super().__post_init__()

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
            interface_names=[interface.name for interface in client_config.interfaces_config().interfaces],
        )
        return FMU2Client(
            _client_config=client_config,
            _image_renderer_service=image_renderer_service,
            _execution_config=execution_config,
            _simulator_config=simulator_config,
            _fmu_instance=simulator_config.create_fmu2_instance(),
        )

    @override
    def _on_initialize_model(
        self,
        start_time: float = 0.0,
    ) -> None:
        self._fmu_instance.instantiate()
        self._fmu_instance.setupExperiment(startTime=start_time)
        self._fmu_instance.enterInitializationMode()
        self._fmu_instance.exitInitializationMode()

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
            self._free_fmu_instance()
        finally:
            self.logger.debug("        ->> removing extracted files...")
            self._remove_extracted_files()

    def _free_fmu_instance(self) -> None:
        # the FMU is extracted on creation, but only instantiated when the simulation starts
        if self._fmu_instance.component is None:
            return
        try:
            if self._is_initialized:
                self.logger.debug("        ->> terminating instance...")
                self._fmu_instance.terminate()
        finally:
            self.logger.debug("        ->> freeing instance...")
            self._fmu_instance.freeInstance()

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
