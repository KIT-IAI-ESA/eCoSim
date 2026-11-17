from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser


@dataclass(frozen=True, kw_only=True)
class PythonConfig:
    module_name: str
    class_name: str
    directory: Path

    @staticmethod
    def of(
        config_parser: ConfigParser,
    ) -> PythonConfig:
        model = config_parser.get_string("python", "model")
        module_name, _, class_name = (name.strip() for name in model.partition(":"))
        # a leading dot is a relative import
        if not module_name or not class_name or module_name.startswith("."):
            raise ValueError(
                f"{config_parser.config_file}: model in [python] needs a module and a class like room:Room, not '{model}'",
            )
        return PythonConfig(module_name=module_name, class_name=class_name, directory=config_parser.config_file.parent.absolute())

    @property
    def model_reference(self) -> str:
        return f"{self.module_name}:{self.class_name}"
