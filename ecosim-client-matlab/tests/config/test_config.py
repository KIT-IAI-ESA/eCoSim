from ecosim_client_matlab.matlab_config import MatlabConfig
from tests.tech.resource_utils import config_parser_for_resource


def test_matlab_config() -> None:
    config = MatlabConfig(config_parser_for_resource("client_config_matlab.ini"))
    assert config.folder_path == "/path/to/scripts/"
