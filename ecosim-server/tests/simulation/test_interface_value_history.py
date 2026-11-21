from __future__ import annotations

import threading

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.simulation.interface_value_history_thread import InterfaceValueHistoryThread
from ecosim_test_common.test_data.generate_client_id import generate_random_client_id
from tests.simulation.history_test_setup import (
    TIMEOUT_IN_SECONDS,
    RecordingRepositories,
    TransactionCountingEntries,
    client_sim_step_data,
    history,
    simulation_config,
    values,
)


def test_add_adds_the_entry_in_an_own_thread(communication_protocol: CommunicationProtocol) -> None:
    repositories = RecordingRepositories()
    client_id = generate_random_client_id()
    value_history = history(
        repositories=repositories,
        communication_protocol=communication_protocol,
        client_id=client_id,
    )

    value_history.add(time_step=0, client_id=client_id, interface_values=values())
    value_history.close()

    repository = repositories.measurement_repository(client_id)
    assert [entry.values for entry in repository.all()] == [values()]
    assert repository.adding_thread_ids != [threading.get_ident()]


def test_add_does_not_wait_for_the_entry_to_be_added() -> None:
    repositories = RecordingRepositories()
    client_id = generate_random_client_id()
    value_history = history(
        repositories,
        blocked=True,
        client_id=client_id,
    )

    repository = repositories.measurement_repository(client_id)

    value_history.add(time_step=0, client_id=client_id, interface_values=values())

    assert repository.add_started.wait(timeout=TIMEOUT_IN_SECONDS), "the adding thread did not start"
    assert repository.all() == [], "'add' returned only after the entry was added"
    repository.blocker.set()
    value_history.close()
    assert len(repository.all()) == 1


def test_the_entries_are_added_in_the_order_they_were_handed_over() -> None:
    repositories = RecordingRepositories()
    client_id = generate_random_client_id()
    value_history = history(
        repositories,
        client_id=client_id,
    )

    for step in range(100):
        value_history.add(time_step=step, client_id=client_id, interface_values=values(float(step)))
    value_history.close()

    assert [entry.values for entry in repositories.measurement_repository(client_id).all()] == [values(float(step)) for step in range(100)]


def test_storing_a_step_does_not_copy_the_entries() -> None:
    repositories = RecordingRepositories()
    client_id = generate_random_client_id()
    entries = TransactionCountingEntries()
    value_history = history(repositories=repositories, client_id=client_id, entries=entries)

    value_history.add(time_step=0, client_id=client_id, interface_values=values())
    value_history.close()

    assert entries.transaction_count == 0


def test_a_reader_sees_the_entries_that_are_still_on_their_way() -> None:
    repositories = RecordingRepositories()
    value_history = history(
        repositories,
        client_id=None,
    )

    for client in simulation_config().clients:
        value_history.add_default_values(client_id=client.client_id, client_sim_step_data=client_sim_step_data())

    assert value_history.contains_all_default_values(), "the reader did not wait for the entries of the adding thread"
    value_history.close()


def test_the_default_values_are_not_added_to_the_repository() -> None:
    repositories = RecordingRepositories()
    client_id = generate_random_client_id()
    value_history = history(
        repositories,
        client_id=client_id,
    )

    value_history.add_default_values(client_id=client_id, client_sim_step_data=client_sim_step_data())
    value_history.close()

    assert repositories.measurement_repository(client_id).all() == []


def test_flush_raises_if_an_entry_could_not_be_added() -> None:
    repositories = RecordingRepositories()
    client_id = generate_random_client_id()
    value_history = history(
        repositories,
        client_id=client_id,
    )
    repositories.measurement_repository(client_id).failure = RuntimeError("db is gone")

    value_history.add(time_step=0, client_id=client_id, interface_values=values())

    with pytest.raises(RuntimeError):
        value_history.flush()
    value_history.close()


def test_close_stops_the_adding_thread() -> None:
    repositories = RecordingRepositories()
    threads_before = _adding_threads()
    client_id = generate_random_client_id()
    value_history = history(
        repositories,
        client_id=client_id,
    )

    value_history.add(time_step=0, client_id=client_id, interface_values=values())
    value_history.close()

    assert _adding_threads() == threads_before
    assert len(repositories.measurement_repository(client_id).all()) == 1


def _adding_threads() -> set[threading.Thread]:
    return {thread for thread in threading.enumerate() if thread.name == InterfaceValueHistoryThread.THREAD_NAME}
