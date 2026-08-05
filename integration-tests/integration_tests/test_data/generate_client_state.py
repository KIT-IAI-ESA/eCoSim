from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_state import ClientState
from ecosim_server.client_connection import ClientConnection
from integration_tests.test_data.generate_client_id import generate_random_client_id
from test_data.generate_client_connection import generate_client_connection


def generate_client_state(
    client_id: ClientID | None = None,
    connected: bool = False,
    connection: ClientConnection | None = None,
) -> ClientState:
    return ClientState(
        client_id=client_id or generate_random_client_id(),
        connected=connected,
        connection=connection,
    )


def generate_client_state_connected(
    client_id: ClientID | None,
    communication_protocol: CommunicationProtocol,
) -> ClientState:
    return generate_client_state(
        client_id=client_id,
        connected=True,
        connection=generate_client_connection(communication_protocol),
    )
