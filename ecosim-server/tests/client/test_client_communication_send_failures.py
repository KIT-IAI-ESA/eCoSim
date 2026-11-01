from datetime import datetime
from typing import Callable
from unittest.mock import MagicMock

import pytest
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequest
from ecosim_common.communication.message_type import MessageType
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.client.client_message_buffer import ClientMessageBuffer
from ecosim_server.client.client_state import ClientState
from ecosim_server.client.client_states import ClientStates

_CLIENT_ID = ClientID(model_name="model", simulator_name="simulator")
_WAIT_IN_SECONDS = 5


def _communication(client_states: MagicMock) -> ClientCommunication:
    return ClientCommunication(
        _client_states=client_states,
        _client_message_buffer=ClientMessageBuffer.for_communication_protocol(CommunicationProtocol.TCP_SOCKET),
    )


def _failing_connection() -> MagicMock:
    connection = MagicMock(spec=ClientConnection)
    connection.send.side_effect = ConnectionError("broken pipe")
    return connection


def _send_step(communication: ClientCommunication) -> None:
    communication.send_simulation_step(current_step=3, client_id=_CLIENT_ID, values=[])


def _send_batch(communication: ClientCommunication) -> None:
    communication.send_simulation_step_batch(
        client_id=_CLIENT_ID,
        data=SimulationStepBatchRequest(start_datetime=datetime(year=2025, month=1, day=1), inputs={}),
    )


_SENDS = [(_send_step, MessageType.SIMULATION_STEP), (_send_batch, MessageType.SIMULATION_STEP_BATCH)]


@pytest.mark.parametrize(("send", "message_type"), _SENDS)
def test_failed_send_reaches_whoever_waits_for_the_answer(
    send: Callable[[ClientCommunication], None],
    message_type: MessageType,
) -> None:
    client_states = MagicMock(spec=ClientStates)
    client_states.get_connection_for.return_value = _failing_connection()
    communication = _communication(client_states)

    with communication.subscribe(client_ids=(_CLIENT_ID,), message_types=(message_type,)) as subscription:
        send(communication)
        with pytest.raises(RuntimeError, match=f"{_CLIENT_ID}.*broken pipe"):
            subscription.next_message(timeout_in_seconds=_WAIT_IN_SECONDS)


@pytest.mark.parametrize(("send", "message_type"), _SENDS)
def test_missing_connection_reaches_whoever_waits_for_the_answer(
    send: Callable[[ClientCommunication], None],
    message_type: MessageType,
) -> None:
    client_states = MagicMock(spec=ClientStates)
    client_states.get_connection_for.return_value = None
    communication = _communication(client_states)

    with communication.subscribe(client_ids=(_CLIENT_ID,), message_types=(message_type,)) as subscription:
        send(communication)
        with pytest.raises(RuntimeError, match=str(_CLIENT_ID)):
            subscription.next_message(timeout_in_seconds=_WAIT_IN_SECONDS)


def test_failed_broadcast_names_the_client() -> None:
    client_states = MagicMock(spec=ClientStates)
    client_states.all_states.return_value = (ClientState(client_id=_CLIENT_ID, connection=_failing_connection()),)

    with pytest.raises(RuntimeError, match=f"{_CLIENT_ID}.*broken pipe"):
        _communication(client_states).broadcast(ESPChannelMessageJson.empty(type=MessageType.SIMULATION_START))
