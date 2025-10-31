from typing import List

from ecosim_common.simulation.interface_id import InterfaceId
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.tech.logger.logger import ESPLogger


class ExecutionConfig:
    _logger = ESPLogger("ExecutionConfig")

    def __init__(
        self,
        step_size_in_ms: int = 1_000,
    ) -> None:
        self._step_size_in_ms: int = step_size_in_ms
        self._server_interface_settings: ServerInterfaceSettings | None = None

    def set_server_interface_settings(
        self,
        server_interface_settings: ServerInterfaceSettings,
    ) -> None:
        self._server_interface_settings = server_interface_settings

    def server_used_inputs(self) -> List[InterfaceId]:
        if self._server_interface_settings is None:
            return []
        return self._server_interface_settings.inputs

    def server_used_outputs(self) -> List[InterfaceId]:
        if self._server_interface_settings is None:
            return []
        return self._server_interface_settings.outputs

    def step_size_in_seconds(self) -> float:
        return self._step_size_in_ms / 1000

    def set_step_size_in_ms(
        self,
        step_size_in_ms: int,
    ) -> None:
        self._step_size_in_ms = step_size_in_ms
