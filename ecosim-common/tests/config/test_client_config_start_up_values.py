from ecosim_common.client.config.client_config import SimpleClientConfig
from ecosim_test_common.resources.resource_utils import config_parser_for_resource


def _client_config() -> SimpleClientConfig:
    return SimpleClientConfig.of_config_parser(config_parser=config_parser_for_resource("configs/common_client_config.ini"))


def test_the_client_config_shows_the_client_its_type_and_how_many_interfaces_it_has() -> None:
    assert _client_config().start_up_values(list_every_interface=False, start_values=[]) == {
        "Simulator name": "Simulator Name",
        "Model name": "Model Name",
        "Simulation type": "fmu_2",
        "Server address": "localhost:1234",
        "Interfaces": "2 inputs, 2 outputs",
    }


def test_one_input_and_one_output_are_counted_in_the_singular() -> None:
    client_config = SimpleClientConfig.of_config_parser(config_parser=config_parser_for_resource("integration/models/fmu3/configs/state_space.ini"))

    assert client_config.start_up_values(list_every_interface=False, start_values=[])["Interfaces"] == "1 input, 1 output"


def test_with_debug_the_client_config_also_lists_every_interface() -> None:
    client_config = _client_config()

    values = client_config.start_up_values(list_every_interface=True, start_values=[])

    assert values["Provided interfaces"] == client_config.interfaces_config().interfaces


def test_the_client_config_lists_every_start_value_also_without_debug() -> None:
    values = _client_config().start_up_values(list_every_interface=False, start_values=["U_wall = 0.3 W/(m2.K)"])

    assert values["Start values"] == ["U_wall = 0.3 W/(m2.K)"]
