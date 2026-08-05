from typing import Any, Generator, Tuple, assert_never

import pytest
from ecosim_common.client.client import Client
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_states import ClientStates
from test_data.pre_sets.pre_set_two_clients import PreSetTwoClientsData

ClientCommunicationData = Tuple[ClientCommunication, ClientStates, CommunicationProtocol]


@pytest.fixture
def _client_communication_setup(pre_set_two_clients: PreSetTwoClientsData) -> Generator[ClientCommunicationData, Any, None]:
    server_wait_thread = pre_set_two_clients.start_server_and_wait_for_all_clients_connected_and_ready()
    pre_set_two_clients.start_client_1_async()
    pre_set_two_clients.start_client_2_async()

    server_wait_thread.join()

    server = pre_set_two_clients.server
    client_communication = server.client_communication()
    client_states = server.client_states()
    yield (client_communication, client_states, server.communication_protocol())
    server.force_stop()


def test_check_client_connection_states_connected(_client_communication_setup: ClientCommunicationData) -> None:
    client_communication, client_states, _ = _client_communication_setup

    client_communication.check_client_connection_states()

    for i, client_state in enumerate(client_states.all_states()):
        assert client_state.connected
        assert client_state.connection is not None


def test_check_client_connection_states_init_not_connected(_client_communication_setup: ClientCommunicationData) -> None:
    client_communication, client_states, _ = _client_communication_setup
    for _, client_id in enumerate(client_states.all_client_ids()):
        client_states.set_client_connected_state(client_id=client_id, connected=False)
    for _, client_state in enumerate(client_states.all_states()):
        assert not client_state.connected

    client_communication.check_client_connection_states()

    for i, client_state in enumerate(client_states.all_states()):
        assert client_state.connected
        assert client_state.connection is not None


def test_check_client_connection_states_connected_but_lost(_client_communication_setup: ClientCommunicationData) -> None:
    client_communication, client_states, communication_protocol = _client_communication_setup
    buffer = Client._handle_ping  # noqa: SLF001
    try:

        def patch_client_handle_ping() -> None:
            Client._handle_ping = lambda _, _m: None  # type: ignore[assignment]  # noqa: SLF001

        # TODO_OSR: somehow extract logic for patching methods
        match communication_protocol:
            case CommunicationProtocol.TCP_SOCKET:
                patch_client_handle_ping()
            case CommunicationProtocol.DASK:
                from dask import distributed

                distributed.get_client().run(patch_client_handle_ping)
            case _:
                assert_never(communication_protocol)

        for _, client_state in enumerate(client_states.all_states()):
            assert client_state.connected

        client_communication.check_client_connection_states()

        for _, client_state in enumerate(client_states.all_states()):
            assert not client_state.connected
            assert client_state.connection is not None
    finally:

        def patch_client_handle_ping() -> None:
            Client._handle_ping = buffer  # type: ignore[method-assign] # noqa: SLF001

        match communication_protocol:
            case CommunicationProtocol.TCP_SOCKET:
                patch_client_handle_ping()
            case CommunicationProtocol.DASK:
                from dask import distributed

                distributed.get_client().run(patch_client_handle_ping)
            case _:
                assert_never(communication_protocol)


def test_closing_connection_unsets_connected(_client_communication_setup: ClientCommunicationData) -> None:
    client_communication, client_states, _ = _client_communication_setup
    for _, client_state in enumerate(client_states.all_states()):
        client_state.connection.close()  # type: ignore[union-attr]

    for _, client_state in enumerate(client_states.all_states()):
        assert not client_state.connected
