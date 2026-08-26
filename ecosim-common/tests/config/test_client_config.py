from unittest.mock import Mock

from ecosim_common.client.config.client_config import ClientInterfaceConfig, ServerConfig, SimpleClientConfig, SimulatorConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.data.server_interface_settings import ServerInterfaceSettings
from ecosim_common.config.interface_type import InterfaceType
from ecosim_common.config.model_interface_client import ModelInterfaceClient
from ecosim_common.simulation.model_interface_id import ModelInterfaceId
from ecosim_test_common.resources.resource_utils import config_parser_for_resource, fmc_path


# #SPEC
def test_load() -> None:
    config_parser = config_parser_for_resource("configs/common_client_config.ini")
    config = SimpleClientConfig.of_config_parser(config_parser)

    # SERVER
    assert config.server_config().server_address.ip == "localhost"
    assert config.server_config().server_address.port == 1234

    # SIMULATOR
    assert config.simulator_config().fmc_file == "fmcs/sub1.fmc"
    assert config.simulator_config().simulator_name == "Simulator Name"
    assert config.simulator_config().model_name == "Model Name"

    # TYPE
    assert config.type() == ClientType.FMU_2

    # INTERFACES
    assert (
        ModelInterfaceClient(
            model_interface_id=ModelInterfaceId(model_name="Model Name", interface="pos_2"),
            name="pos_2",
            unit="m",
            description="",
            required=False,
            type=InterfaceType.INPUT,
        )
        in config.interfaces_config().interfaces
    )
    assert (
        ModelInterfaceClient(
            model_interface_id=ModelInterfaceId(model_name="Model Name", interface="speed_2"),
            name="speed_2",
            type=InterfaceType.INPUT,
            unit="m/s",
            description="",
            required=False,
        )
        in config.interfaces_config().interfaces
    )
    assert (
        ModelInterfaceClient(
            model_interface_id=ModelInterfaceId(model_name="Model Name", interface="pos_1"),
            name="pos_1",
            type=InterfaceType.OUTPUT,
            unit="m",
            description="",
            required=False,
        )
        in config.interfaces_config().interfaces
    )
    assert (
        ModelInterfaceClient(
            model_interface_id=ModelInterfaceId(model_name="Model Name", interface="speed_1"),
            name="speed_1",
            type=InterfaceType.OUTPUT,
            unit="m/s",
            description="",
            required=False,
        )
        in config.interfaces_config().interfaces
    )


# #SPEC
def test_meta_data() -> None:
    config_parser = config_parser_for_resource("configs/common_client_config.ini")
    config = SimpleClientConfig.of_config_parser(config_parser)

    assert config.meta_data() == ClientMetaData(
        version="2.0",
        simulator_name="Simulator Name",
        model_name="Model Name",
    )


# #SPEC
def test_json_string_interfaces() -> None:
    simulator_config = Mock(spec=SimulatorConfig)
    simulator_config.fmc_file = "fmc_interface_test.fmc"
    simulator_config.ensemble = "Test_Ensemble"
    simulator_config.model_name = "Model_Name"
    config = ClientInterfaceConfig.of_simulator_config(simulator_config=simulator_config, config_path=fmc_path())
    expected = (
        "["
        '{"model_interface_id": {"model_name": "Model_Name", "interface": "input_1"}, "name": "input_1", "unit": "m", "description": "non required value", "type": "input", "required": false}, '  # noqa: E501
        '{"model_interface_id": {"model_name": "Model_Name", "interface": "input_2"}, "name": "input_2", "unit": "m/s", "description": "required value", "type": "input", "required": true}, '  # noqa: E501
        '{"model_interface_id": {"model_name": "Model_Name", "interface": "input_3"}, "name": "input_3", "unit": "m/s", "description": "missing required attribute", "type": "input", "required": false}, '  # noqa: E501
        '{"model_interface_id": {"model_name": "Model_Name", "interface": "output_1"}, "name": "output_1", "unit": "m", "description": "output 1", "type": "output", "required": false}, '  # noqa: E501
        '{"model_interface_id": {"model_name": "Model_Name", "interface": "output_2"}, "name": "output_2", "unit": "m/s", "description": "output 2", "type": "output", "required": false}'  # noqa: E501
        "]"
    )
    actual = config.all_interfaces_to_protocol_json_string()
    assert actual == expected


# #SPEC
def test_validate_interface_config_with_actual() -> None:
    simulator_config = Mock(spec=ClientInterfaceConfig)
    simulator_config.fmc_file = "fmc_interface_test.fmc"
    simulator_config.ensemble = "Test_Ensemble"
    simulator_config.model_name = "Model_Name"
    config = ClientInterfaceConfig.of_simulator_config(simulator_config=simulator_config, config_path=fmc_path())
    actual_input_only_required = ["input_2"]
    actual_input_missing_required = ["input_1", "input_3"]
    actual_input_all = ["input_1", "input_2", "input_3"]
    actual_input_all_plus_non_matching = ["input_1", "input_2", "input_3", "non_matching"]
    actual_output_all = ["output_1", "output_2"]
    actual_output_all_plus_non_matching = ["output_1", "output_2", "non_matching"]
    assert (
        config.validate_config_with_server(
            ServerInterfaceSettings(
                inputs=actual_input_only_required,
                outputs=actual_output_all,
            ),
        )
        is True
    )
    assert (
        config.validate_config_with_server(
            ServerInterfaceSettings(inputs=actual_input_all, outputs=actual_output_all),
        )
        is True
    )
    assert (
        config.validate_config_with_server(
            ServerInterfaceSettings(inputs=actual_input_missing_required, outputs=actual_output_all),
        )
        is False
    )
    assert (
        config.validate_config_with_server(
            ServerInterfaceSettings(inputs=actual_input_all_plus_non_matching, outputs=actual_output_all),
        )
        is False
    )
    assert (
        config.validate_config_with_server(
            ServerInterfaceSettings(inputs=actual_input_all, outputs=actual_output_all_plus_non_matching),
        )
        is False
    )


def test_as_config_file_content() -> None:
    config = SimpleClientConfig(
        _server_config=ServerConfig(
            server_address=ConnectionAddress("localhost", 222),
            image_renderer_port=333,
            communication_protocol=CommunicationProtocol.TCP_SOCKET,
        ),
        _simulator_config=SimulatorConfig(
            simulator_name="simulator",
            model_name="model",
            fmc_file="fmc_file",
            type=ClientType.FMU_3,
        ),
        _interfaces_config=ClientInterfaceConfig(interfaces=[]),
        _extra_sections=[],
    )

    file_content = config.as_config_file_content()
    assert (
        file_content
        == """
[server]
ip = localhost
port = 222
communication_protocol = tcp_socket

[simulator]
simulator_name = simulator
model_name = model
fmc_file = fmc_file
type = fmu_3
""".strip()
    )
