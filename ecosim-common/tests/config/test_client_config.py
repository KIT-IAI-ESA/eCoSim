import json
from pathlib import Path
from unittest.mock import Mock

import pytest
from ecosim_common.client.config.client_config import ClientInterfaceConfig, ServerConfig, SimpleClientConfig, SimulatorConfig
from ecosim_common.client.config.client_type import ClientType
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.config.config_parser import ConfigParser
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


def _simulator_config_with_fmc_file(fmc_file: str) -> SimulatorConfig:
    return SimulatorConfig(simulator_name="house", model_name="house", fmc_file=fmc_file, type=ClientType.FMU_2)


def test_a_missing_fmc_file_shows_its_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as error_info:
        ClientInterfaceConfig.of_simulator_config(simulator_config=_simulator_config_with_fmc_file(fmc_file="hous.fmc"), config_path=tmp_path)

    assert error_info.value.filename == str(tmp_path / "hous.fmc")


def test_an_fmc_file_that_is_not_json_shows_the_file(tmp_path: Path) -> None:
    fmc_file = tmp_path / "house.fmc"
    fmc_file.write_text('{"inputs": [] "outputs": []}', encoding="utf-8")

    with pytest.raises(ValueError) as error_info:
        ClientInterfaceConfig.of_simulator_config(simulator_config=_simulator_config_with_fmc_file(fmc_file="house.fmc"), config_path=tmp_path)

    assert str(error_info.value).startswith(f"{fmc_file} is not valid JSON")


@pytest.mark.parametrize("unnamed_output", [{"unit": "W"}, {"name": ""}], ids=["missing name", "empty name"])
def test_an_output_without_a_name_shows_the_file_and_the_output(tmp_path: Path, unnamed_output: dict[str, str]) -> None:
    fmc_file = tmp_path / "house.fmc"
    fmc_file.write_text(json.dumps({"outputs": [{"name": "T_indoor"}, unnamed_output]}), encoding="utf-8")

    with pytest.raises(ValueError) as error_info:
        ClientInterfaceConfig.of_simulator_config(simulator_config=_simulator_config_with_fmc_file(fmc_file="house.fmc"), config_path=tmp_path)

    assert str(error_info.value) == f"{fmc_file}: the output at index 1 has no name."


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
communication_protocol = TCP_SOCKET

[simulator]
simulator_name = simulator
model_name = model
fmc_file = [fmc_file]
type = fmu_3
""".strip()
    )


def test_a_written_client_config_reads_back_the_same(tmp_path: Path) -> None:
    server_config = ServerConfig(
        server_address=ConnectionAddress(ip="localhost", port=1234),
        communication_protocol=CommunicationProtocol.DASK,
    )
    simulator_config = SimulatorConfig(simulator_name="house", model_name="house", fmc_file="house.fmc", type=ClientType.FMU_2)
    config_file = tmp_path / "preferences.ini"
    config_file.write_text(
        SimpleClientConfig(
            _server_config=server_config,
            _simulator_config=simulator_config,
            _interfaces_config=ClientInterfaceConfig(interfaces=[]),
            _extra_sections=[],
        ).as_config_file_content(),
        encoding="utf-8",
    )

    config_parser = ConfigParser(path=config_file)

    assert ServerConfig.of_config_parser(config=config_parser) == server_config
    assert SimulatorConfig.of_config_parser(config=config_parser) == simulator_config
