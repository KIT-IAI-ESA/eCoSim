from typing import Tuple

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_server.client.client_state import ClientState
from ecosim_server.client.client_states import ClientStates
from ecosim_test_common.test_data.generate_client_id import generate_random_client_id
from integration_tests.test_data.generate_client_state import generate_client_state


def _connected_client_states(
    communication_protocol: CommunicationProtocol,
    client_ids: Tuple[ClientID, ...],
) -> ClientStates:
    return ClientStates._for_clients_and_protocol(  # noqa: SLF001
        communication_protocol=communication_protocol,
        init_clients={client_id: generate_client_state(client_id=client_id, connected=True) for client_id in client_ids},
    )


def test_all_client_ids_does_not_read_the_shared_map(communication_protocol: CommunicationProtocol) -> None:
    """The client ids are static configuration, so asking for them must not cost a read of the shared state."""
    client_ids = (generate_random_client_id(), generate_random_client_id())
    client_states = _connected_client_states(communication_protocol, client_ids)
    shared_map = client_states._client_states  # noqa: SLF001
    reads = 0
    original_get_snapshot = type(shared_map).get_snapshot

    def counting_get_snapshot(counted_map: ESPMap[ClientID, ClientState]) -> dict[ClientID, ClientState]:
        nonlocal reads
        reads += 1
        return original_get_snapshot(counted_map)

    type(shared_map).get_snapshot = counting_get_snapshot  # type: ignore[method-assign]
    try:
        assert set(client_states.all_client_ids()) == set(client_ids)
    finally:
        type(shared_map).get_snapshot = original_get_snapshot  # type: ignore[method-assign]

    assert reads == 0


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
