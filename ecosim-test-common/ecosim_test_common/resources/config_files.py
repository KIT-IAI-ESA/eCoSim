from pathlib import Path

from ecosim_test_common.resources.resource_utils import resource_path

BASE_CONFIG_DIR = "configs"


def config_file_path(config: str) -> Path:
    return resource_path() / BASE_CONFIG_DIR / config


def config_file_path_str(config: str) -> str:
    return str(config_file_path(config).absolute())
