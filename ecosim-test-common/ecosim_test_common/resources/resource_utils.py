from pathlib import Path

from ecosim_common.config import config_parser
from ecosim_common.config.config_parser import ConfigParser


def config_parser_for_resource(resource_name: str) -> ConfigParser:
    return config_parser.ConfigParser(resource_path() / resource_name)


def resource_path() -> Path:
    return Path(__file__).parent.parent / "resources"


def resource_path_file(file: str) -> Path:
    return resource_path() / file


def resource_path_file_str(file: str) -> str:
    return f"{resource_path_file(file)}"


def fmc_path() -> Path:
    return resource_path_file("configs/fmcs")


def fmu2_model_path() -> Path:
    return resource_path_file("integration/models/fmu2/Feedthrough.fmu")


def fmu2_fmc_path() -> Path:
    return resource_path_file("integration/models/fmu2/configs/Feedthrough.fmc")


def fmu3_model_path() -> Path:
    return resource_path_file("integration/models/fmu3/StateSpace.fmu")


def fmu3_fmc_path() -> Path:
    return resource_path_file("integration/models/fmu3/configs/StateSpace.fmc")


def python_room_config_path() -> Path:
    return resource_path_file("python/room/preferences.ini")
