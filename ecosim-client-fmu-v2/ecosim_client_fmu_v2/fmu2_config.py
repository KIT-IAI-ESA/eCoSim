from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser


@dataclass(frozen=True)
class FMU2Config:
    fmu_file: Path

    @classmethod
    def of_config_parser(cls,
                         config_parser: ConfigParser
                         ) -> FMU2Config:
        fmu_file = (config_parser.config_file.parent / config_parser.get_string_array('fmu', 'fmu_file')[0]).absolute()
        return FMU2Config(
            fmu_file=fmu_file,
        )
