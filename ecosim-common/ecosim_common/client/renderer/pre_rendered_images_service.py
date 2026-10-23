from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, override

from ecosim_common.client.renderer.simulation_renderer_service import SimulationRendererService
from ecosim_common.tech.logger.logger import ESPLogger


@dataclass(kw_only=True)
class PreRenderedImageService(SimulationRendererService):
    _logger: ClassVar[ESPLogger] = ESPLogger("PreRenderedImageService")
    _file_pattern: ClassVar[re.Pattern[str]] = re.compile(r"^(\d+)_")

    _config: PreRenderedImageServiceConfig

    @staticmethod
    def of_config_path(config_path: Path) -> SimulationRendererService:
        pre_rendered_images_dir = os.path.dirname(config_path) + "/rendered_images"
        PreRenderedImageService._logger.debug("Pre-rendered images dir: '%s'.", pre_rendered_images_dir)
        return PreRenderedImageService(
            _config=PreRenderedImageServiceConfig(
                image_dir=pre_rendered_images_dir,
            ),
        )

    @override
    def render_step(
        self,
        time_step: int,
    ) -> bytes | None:
        try:
            for file_path in Path(self._config.image_dir).iterdir():
                if not file_path.is_file():
                    continue
                match = self._file_pattern.match(file_path.name)
                if not match:
                    continue
                number = int(match.group(1))
                if number == time_step:
                    PreRenderedImageService._logger.debug("Found pre-rendered image in '%s' for time step %s", self._config.image_dir, time_step)
                    with open(file_path, "rb") as file:
                        return file.read()
        except Exception as e:
            PreRenderedImageService._logger.error("Failed to render image %s", e)
            return None
        PreRenderedImageService._logger.error("Failed to find pre-rendered image in '%s' for time step %s", self._config.image_dir, time_step)
        return None


class PreRenderedImageServiceConfig:
    def __init__(
        self,
        image_dir: str,
    ):
        self.image_dir: str = image_dir
