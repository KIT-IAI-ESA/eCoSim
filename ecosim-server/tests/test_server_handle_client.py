from unittest.mock import MagicMock

import pytest
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.server import Server


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
