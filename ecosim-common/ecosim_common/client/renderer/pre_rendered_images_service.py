from __future__ import annotations

import re
from pathlib import Path

from ecosim_common.client.renderer.simulation_renderer_service import SimulationRendererService
from ecosim_common.tech.logger.logger import ESPLogger


class PreRenderedImageService(SimulationRendererService):
    _logger = ESPLogger("PreRenderedImageService")

    def __init__(
        self,
        config: PreRenderedImageServiceConfig,
    ) -> None:
        self._config: PreRenderedImageServiceConfig = config
        self._file_pattern = re.compile(r"^(\d+)_")

    def render_step(
        self,
        time_step: int,
    ) -> bytes | None:
        try:
            # Iterate over all files in directory
            for file_path in Path(self._config.image_dir).iterdir():
                if not file_path.is_file():
                    continue
                match = self._file_pattern.match(file_path.name)
                if not match:
                    continue
                number = int(match.group(1))
                if number == time_step:
                    PreRenderedImageService._logger.debug(
                        f"Found pre-rendered image in '{self._config.image_dir}' for time step {time_step}",
                    )
                    with open(file_path, "rb") as file:
                        return file.read()
        except Exception as e:
            PreRenderedImageService._logger.error("Failed to render image {}".format(e))
            return None
        PreRenderedImageService._logger.error(
            f"Failed to find pre-rendered image in '{self._config.image_dir}' for time step {time_step}",
        )
        return None


class PreRenderedImageServiceConfig:
    def __init__(
        self,
        image_dir: str,
    ):
        self.image_dir: str = image_dir
