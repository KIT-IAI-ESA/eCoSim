from ecosim_common.client.config.client_config import ClientInterfaceConfig, SimulatorConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_test_common.resources.resource_utils import fmc_path


def _mismatch_lines(server_interface_settings: ServerInterfaceSettings) -> list[str]:
    # the test .fmc has the inputs input_1, input_2 (required) and input_3, and the outputs output_1 and output_2
    simulator_config = SimulatorConfig(simulator_name="model", model_name="model", fmc_file="fmc_interface_test.fmc", type=ClientType.FMU_2)
    interfaces_config = ClientInterfaceConfig.of_simulator_config(simulator_config=simulator_config, config_path=fmc_path())
    return interfaces_config.validate_config_with_server(server_config=server_interface_settings).lines(fmc_file="model.fmc")


def test_interfaces_that_match_the_fmc_file_give_no_mismatch() -> None:
    assert _mismatch_lines(ServerInterfaceSettings(inputs=["input_1", "input_2"], outputs=["output_1"])) == []


def test_an_input_the_fmc_file_does_not_list_is_named_with_the_close_name() -> None:
    assert _mismatch_lines(ServerInterfaceSettings(inputs=["input_2", "input_33"], outputs=[])) == [
        "The simulation config connects input input_33, but model.fmc has no input of that name. Did you mean input_3?",
    ]


def test_an_output_the_fmc_file_does_not_list_is_named() -> None:
    assert _mismatch_lines(ServerInterfaceSettings(inputs=["input_2"], outputs=["temperature"])) == [
        "The simulation config reads output temperature, but model.fmc has no output of that name.",
    ]


def test_a_required_input_the_simulation_config_does_not_connect_is_named() -> None:
    assert _mismatch_lines(ServerInterfaceSettings(inputs=["input_1"], outputs=[])) == [
        "model.fmc marks input input_2 as required, but the simulation config does not connect it.",
    ]


def test_an_input_that_only_shares_the_start_of_a_name_in_the_fmc_file_gets_no_hint() -> None:
    assert _mismatch_lines(ServerInterfaceSettings(inputs=["input_2", "input_dry"], outputs=[])) == [
        "The simulation config connects input input_dry, but model.fmc has no input of that name.",
    ]
