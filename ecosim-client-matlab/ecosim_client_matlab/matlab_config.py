from pathlib import Path
from typing import ClassVar

from ecosim_common.config.config_parser import ConfigParser


class MatlabConfig:
    SCRIPT_NAMES: ClassVar[tuple[str, ...]] = ("setup.m", "step.m", "finishing.m")

    def __init__(
        self,
        config: ConfigParser,
    ):
        self.folder_path: Path = (config.config_file.parent / config.get_string("matlab", "scriptfolder")).absolute()
        self._ensure_scripts_exist()

    def _ensure_scripts_exist(self) -> None:
        missing_scripts = [name for name in MatlabConfig.SCRIPT_NAMES if not (self.folder_path / name).is_file()]
        if missing_scripts:
            raise FileNotFoundError(f"The script folder {self.folder_path} is missing {', '.join(missing_scripts)}")
