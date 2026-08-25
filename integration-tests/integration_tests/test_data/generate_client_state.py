from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.client.client_state import ClientState
from ecosim_test_common.test_data.generate_client_id import generate_random_client_id


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
