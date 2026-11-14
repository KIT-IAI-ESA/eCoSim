from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser


@dataclass(frozen=True, kw_only=True)
class PythonConfig:
    module_name: str
    class_name: str
    # on the import path first, so a module next to the ini file wins over an installed one
    folder: Path

    @staticmethod
    def of(
        config_parser: ConfigParser,
    ) -> PythonConfig:
        # section and key without names, so dev/generate_config_reference.py finds them
        model = config_parser.get_string("python", "model")
        module_name, _, class_name = (name.strip() for name in model.partition(":"))
        # a leading dot is a relative import, which has no package to start from here
        if not module_name or not class_name or module_name.startswith("."):
            raise ValueError(
                f"{config_parser.config_file}: model in [python] has to name a module and a class, like model = room:Room, not '{model}'",
            )
        return PythonConfig(module_name=module_name, class_name=class_name, folder=config_parser.config_file.parent.absolute())

    @property
    def model_reference(self) -> str:
        return f"{self.module_name}:{self.class_name}"
