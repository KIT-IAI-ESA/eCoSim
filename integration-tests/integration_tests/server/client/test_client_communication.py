import threading
from time import sleep
from typing import Any, Generator, Tuple, assert_never

import dask.distributed as distributed
import pytest
from ecosim_common.client.client import Client
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_states import ClientStates
from integration_tests.test_data.pre_sets.pre_set_two_clients import PreSetTwoClientsData

ClientCommunicationData = Tuple[ClientCommunication, ClientStates, CommunicationProtocol]

_test_logger = ESPLogger("TestLogger")


@pytest.fixture
def _client_communication_setup(pre_set_two_clients: PreSetTwoClientsData) -> Generator[ClientCommunicationData, Any, None]:
    server_wait_thread = pre_set_two_clients.start_server_and_wait_for_all_clients_connected_and_ready()
    pre_set_two_clients.start_client_1_async()
    pre_set_two_clients.start_client_2_async()

    server_wait_thread.join(timeout=16)
    if server_wait_thread.is_alive():
        raise Exception("Server did not start within timeout")

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

        client_communication.check_client_connection_states(
            attempts=3,
            time_between_attempts_in_seconds=0.3,
        )

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
    client_communication, client_states, communication_protocol = _client_communication_setup
    for _, client_state in enumerate(client_states.all_states()):
        client_state.connection.close()  # type: ignore[union-attr]

    def check_if_all_clients_disconnected() -> None:
        _test_logger.info("Waiting for clients to disconnect...")
        while any(client_state.connected for client_state in client_states.all_states()):
            sleep(0.1)
        _test_logger.info("Waiting for clients to disconnect...done")

    match communication_protocol:
        case CommunicationProtocol.DASK:
            future = distributed.get_client().submit(check_if_all_clients_disconnected)
            try:
                future.result(timeout=1000)
            except Exception as e:
                assert False, f"Exception while waiting for clients to disconnect: {e}"
        case CommunicationProtocol.TCP_SOCKET:
            waiting_thread = threading.Thread(target=check_if_all_clients_disconnected, daemon=True)
            waiting_thread.start()
            waiting_thread.join(10)
            assert not waiting_thread.is_alive()
