from pathlib import Path

from ecosim_common.config import config_parser
from ecosim_common.config.config_parser import ConfigParser


def config_parser_for_resource(resource_name: str) -> ConfigParser:
    return config_parser.ConfigParser(resource_path() / resource_name)


def resource_path() -> Path:
    return Path(__file__).parent.parent.parent / "resources"


def resource_path_file(file: str) -> Path:
    return resource_path() / file
