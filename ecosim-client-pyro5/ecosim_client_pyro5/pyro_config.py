from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser


@dataclass(kw_only=True)
class PyroConfig:
    config_file: Path
    host: str
    port: str
    object_name: str

    @staticmethod
    def of(
        config_parser: ConfigParser,
    ) -> PyroConfig:
        return PyroConfig(
            config_file=config_parser.config_file,
            host=config_parser.get_string("pyro", "pyro_host"),
            port=config_parser.get_string("pyro", "pyro_port"),
            object_name=config_parser.get_string("pyro", "pyro_object_name"),
        )
