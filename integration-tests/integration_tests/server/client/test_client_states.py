from typing import Tuple

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_states import ClientStates
from integration_tests.test_data.generate_client_id import generate_random_client_id
from integration_tests.test_data.generate_client_state import generate_client_state


def _connected_client_states(
    communication_protocol: CommunicationProtocol,
    client_ids: Tuple[ClientID, ...],
) -> ClientStates:
    return ClientStates._for_clients_and_protocol(  # noqa: SLF001
        communication_protocol=communication_protocol,
        init_clients={client_id: generate_client_state(client_id=client_id, connected=True) for client_id in client_ids},
    )


def test_lost_client_counts_as_stopped(communication_protocol: CommunicationProtocol) -> None:
    client_id = generate_random_client_id()
    client_states = _connected_client_states(communication_protocol, (client_id,))
    assert not client_states.have_all_clients_stopped_simulation()

    client_states.set_client_connected_state(client_id=client_id, connected=False)

    assert client_states.have_all_clients_stopped_simulation()


def test_all_clients_stopped_needs_every_client(communication_protocol: CommunicationProtocol) -> None:
    client_id_1 = generate_random_client_id()
    client_id_2 = generate_random_client_id()
    client_states = _connected_client_states(communication_protocol, (client_id_1, client_id_2))

    client_states.simulation_stopped(client_id=client_id_1)
    assert not client_states.have_all_clients_stopped_simulation()

    client_states.set_client_connected_state(client_id=client_id_2, connected=False)
    assert client_states.have_all_clients_stopped_simulation()


def test_lost_client_is_not_ready_anymore(communication_protocol: CommunicationProtocol) -> None:
    client_id = generate_random_client_id()
    client_states = _connected_client_states(communication_protocol, (client_id,))
    client_states.set_client_ready_for_simulation(client_id=client_id)
    assert client_states.are_all_clients_connected_and_ready()
    assert client_states._all_clients_ready_for_simulation.is_set()  # noqa: SLF001

    client_states.set_client_connected_state(client_id=client_id, connected=False)

    assert not client_states.are_all_clients_connected_and_ready()
    assert not client_states._all_clients_ready_for_simulation.is_set()  # noqa: SLF001


def test_reconnected_client_is_not_stopped_anymore(communication_protocol: CommunicationProtocol) -> None:
    client_id = generate_random_client_id()
    client_states = _connected_client_states(communication_protocol, (client_id,))
    client_states.set_client_connected_state(client_id=client_id, connected=False)
    assert client_states.have_all_clients_stopped_simulation()

    client_states.set_client_connected_state(client_id=client_id, connected=True)

    assert not client_states.have_all_clients_stopped_simulation()
