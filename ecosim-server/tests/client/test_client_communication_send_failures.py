from unittest.mock import MagicMock

import pytest
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.client.client_message_buffer import ClientMessageBuffer
from ecosim_server.client.client_state import ClientState
from ecosim_server.client.client_states import ClientStates


def test_failed_broadcast_names_the_client() -> None:
    client_id = ClientID(model_name="model", simulator_name="simulator")
    failing_connection = MagicMock(spec=ClientConnection)
    failing_connection.send.side_effect = ConnectionError("broken pipe")
    client_states = MagicMock(spec=ClientStates)
    client_states.all_states.return_value = (ClientState(client_id=client_id, connection=failing_connection),)
    communication = ClientCommunication(
        _client_states=client_states,
        _client_message_buffer=ClientMessageBuffer.for_communication_protocol(CommunicationProtocol.TCP_SOCKET),
    )

    with pytest.raises(RuntimeError, match=f"{client_id}.*broken pipe"):
        communication.broadcast(ESPChannelMessageJson.empty(type=MessageType.SIMULATION_START))
