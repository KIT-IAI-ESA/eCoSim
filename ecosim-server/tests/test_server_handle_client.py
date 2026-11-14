import logging
from unittest.mock import MagicMock

import pytest
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.server import Server
from tests.data.generate_postgres_name_config import generate_client_simulator_config, generate_simulation_config


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


def test_a_client_the_simulation_config_does_not_know_is_turned_away_as_unknown() -> None:
    reason = Server.why_the_client_is_turned_away(
        simulation_config=generate_simulation_config(clients=[generate_client_simulator_config(simulator_name="house")]),
        client_id=ClientID(model_name="house", simulator_name="hous"),
    )

    assert reason == "Client house#hous is not in the simulation config, so the server closed its connection"


def test_a_second_client_with_a_known_name_is_turned_away_as_already_connected() -> None:
    reason = Server.why_the_client_is_turned_away(
        simulation_config=generate_simulation_config(clients=[generate_client_simulator_config(simulator_name="house")]),
        client_id=ClientID(model_name="house", simulator_name="house"),
    )

    assert reason == "Client house#house is already connected, so the server closed the second connection"


def test_the_warning_for_a_turned_away_client_names_the_clients_the_server_still_waits_for() -> None:
    warning = Server.turned_away_warning(
        simulation_config=generate_simulation_config(clients=[generate_client_simulator_config(simulator_name="house")]),
        client_id=ClientID(model_name="house", simulator_name="hous"),
        waiting_for_client_ids=(ClientID(model_name="house", simulator_name="house"),),
    )

    assert warning == "Client house#hous is not in the simulation config, so the server closed its connection. Still waiting for: house#house"


def test_the_warning_for_a_turned_away_client_names_no_waiting_when_every_client_is_there() -> None:
    warning = Server.turned_away_warning(
        simulation_config=generate_simulation_config(clients=[generate_client_simulator_config(simulator_name="house")]),
        client_id=ClientID(model_name="house", simulator_name="house"),
        waiting_for_client_ids=(),
    )

    assert warning == "Client house#house is already connected, so the server closed the second connection"


def _closed_connection_records(server_is_running: bool, caplog: pytest.LogCaptureFixture) -> list[tuple[int, str]]:
    caplog.set_level(logging.DEBUG, logger="Server")
    Server.log_closed_connection(
        server_running_event=ParallelEvent.thread(init_set=server_is_running),
        client_id=ClientID(model_name="house", simulator_name="house"),
    )
    return [(record.levelno, record.getMessage()) for record in caplog.records if record.name == "Server"]


def test_a_client_that_closes_its_connection_during_the_run_is_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    assert _closed_connection_records(server_is_running=True, caplog=caplog) == [(logging.WARNING, "Client house#house closed the connection")]


def test_clients_that_close_their_connection_after_the_run_are_only_a_debug_message(caplog: pytest.LogCaptureFixture) -> None:
    assert _closed_connection_records(server_is_running=False, caplog=caplog) == [(logging.DEBUG, "Client house#house closed the connection")]
