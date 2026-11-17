import logging
import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.data.model_interface_ids import ModelInterfaceIds
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.server import Server
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_output, create_simulator
from tests.data.generate_postgres_name_config import generate_client_simulator_config, generate_simulation_config
from tests.data.generate_simulation_config import HOUSE


def _handle_client(
    channel: MagicMock,
    client_communication: MagicMock,
) -> None:
    Server.handle_client(
        server_running_event=MagicMock(),
        client_communication=client_communication,
        simulation_config=MagicMock(spec=SimulationConfig),
        connection=ClientConnection(_channel=channel, address=ConnectionAddress(ip="127.0.0.1", port=1)),
    )


def test_failed_send_before_the_client_is_known_raises_the_connection_error() -> None:
    channel = MagicMock(spec=ESPChannel)
    channel.send.side_effect = ConnectionError("client is gone")

    with pytest.raises(ConnectionError, match="client is gone"):
        _handle_client(channel=channel, client_communication=MagicMock(spec=ClientCommunication))


def test_closed_connection_before_the_client_is_known_raises_a_type_error() -> None:
    channel = MagicMock(spec=ESPChannel)
    channel.listen_blocking.return_value = None

    with pytest.raises(TypeError, match="but received None"):
        _handle_client(channel=channel, client_communication=MagicMock(spec=ClientCommunication))


def test_failed_handshake_of_a_known_client_resets_its_state() -> None:
    meta_data = ClientMetaData(version="1", simulator_name="simulator", model_name="model")
    channel = MagicMock(spec=ESPChannel)
    channel.listen_blocking.side_effect = [
        ESPChannelMessageJson.create(type=MessageType.CLIENT_META_DATA_REQUEST, payload=meta_data),
        None,
    ]
    client_communication = MagicMock(spec=ClientCommunication)
    client_communication.add_if_needed.return_value = True

    with pytest.raises(TypeError, match="but received None"):
        _handle_client(channel=channel, client_communication=client_communication)

    client_communication.reset_state.assert_called_once_with(ClientID(model_name="model", simulator_name="simulator"))


def test_a_client_whose_fmc_file_lacks_a_required_interface_is_rejected(tmp_path: Path) -> None:
    file = config_file(tmp_path, create_simulator("weather", {**create_output("T_out"), "required": "true"}, create_output("rain")))
    channel = MagicMock(spec=ESPChannel)
    channel.listen_blocking.return_value = ESPChannelMessageJson.create(type=MessageType.INTERFACE_REQUEST, payload=ModelInterfaceIds(interfaces=[]))
    client_communication = MagicMock(spec=ClientCommunication)

    message = "The simulation config marks T_out of weather#weather as required, but its .fmc file does not list it."

    with pytest.raises(RuntimeError, match=re.escape(message)):
        Server.handle_interface_request(
            client_communication=client_communication,
            simulation_config=SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=1),
            client_id=ClientID(model_name="weather", simulator_name="weather"),
            connection=ClientConnection(_channel=channel, address=ConnectionAddress(ip="127.0.0.1", port=1)),
        )

    client_communication.interfaces_validated.assert_not_called()


@pytest.mark.parametrize(
    ("simulator_name", "reason"),
    [
        ("house", "Rejected a second connection of client house#house. It is already connected."),
        ("hous", "Rejected client house#hous. It is not in the simulation config. Did you mean house#house?"),
    ],
)
def test_the_warning_for_a_rejected_client_says_why(simulator_name: str, reason: str) -> None:
    warning = Server.rejected_client_warning(
        simulation_config=generate_simulation_config(clients=[generate_client_simulator_config(simulator_name="house")]),
        client_id=ClientID(model_name="house", simulator_name=simulator_name),
        waiting_for_client_ids=(),
    )

    assert warning == reason


def test_the_warning_for_a_rejected_client_lists_the_clients_the_server_still_waits_for() -> None:
    warning = Server.rejected_client_warning(
        simulation_config=generate_simulation_config(clients=[generate_client_simulator_config(simulator_name="house")]),
        client_id=ClientID(model_name="house", simulator_name="hous"),
        waiting_for_client_ids=(HOUSE,),
    )

    assert warning.endswith(" Still waiting for: house#house")


@pytest.mark.parametrize(("server_is_running", "level"), [(True, logging.WARNING), (False, logging.DEBUG)])
def test_a_closed_connection_is_a_warning_only_during_the_run(server_is_running: bool, level: int, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="Server")

    Server.log_closed_connection(server_running_event=ParallelEvent.thread(init_set=server_is_running), client_id=HOUSE)

    assert [record.levelno for record in caplog.records if record.name == "Server"] == [level]
