from __future__ import annotations

from typing import List, Tuple

from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequestInputs
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import ClientSimulatorConfig
from ecosim_server.simulation.restore_data import RestoreData
from tests.simulation.history_test_setup import RecordingRepositories, history, simulation_config


def test_an_incomplete_newest_row_is_not_replayed() -> None:
    repositories = RecordingRepositories()
    weather = simulation_config().clients[0]
    for client in simulation_config().clients:
        _store_completed_steps(repositories=repositories, client=client, steps=5)
    # without its second interface, so the step was not completed
    _store_step(repositories=repositories, client_id=weather.client_id, step=5, interface_values=_every_interface_value(client=weather)[:1])

    restore_data = _restore_data(repositories=repositories)

    assert _steps_of(batch=restore_data.client_restore_data[weather.client_id]) == [0, 1, 2, 3, 4]


def test_a_client_without_a_stored_step_restarts_the_run_at_step_0() -> None:
    repositories = RecordingRepositories()
    _store_completed_steps(repositories=repositories, client=simulation_config().clients[0], steps=1)

    restore_data = _restore_data(repositories=repositories)

    assert restore_data == RestoreData(current_step=0, client_restore_data={client.client_id: {} for client in simulation_config().clients})


def _restore_data(repositories: RecordingRepositories) -> RestoreData:
    value_history = history(repositories=repositories, client_id=None)
    value_history.init_from_repositories()
    restore_data = value_history.calculate_restore_data_or_exception()
    value_history.close()
    return restore_data


def _store_completed_steps(
    repositories: RecordingRepositories,
    client: ClientSimulatorConfig,
    steps: int,
) -> None:
    for step in range(steps):
        _store_step(repositories=repositories, client_id=client.client_id, step=step, interface_values=_every_interface_value(client=client))


def _store_step(
    repositories: RecordingRepositories,
    client_id: ClientID,
    step: int,
    interface_values: Tuple[ProtocolInterfaceValue, ...],
) -> None:
    repository = repositories.measurement_repository(client_id=client_id)
    # stored by the aborted run, so nothing holds the write back
    repository.blocker.set()
    repository.add(values=interface_values, timestamp=simulation_config().date_time_for_step(step))


def _every_interface_value(client: ClientSimulatorConfig) -> Tuple[ProtocolInterfaceValue, ...]:
    return tuple(ProtocolInterfaceValue(name=interface.name, value=1.0) for interface in client.interfaces)


def _steps_of(batch: SimulationStepBatchRequestInputs) -> List[int]:
    return sorted(simulation_config().date_time_to_step(timestamp) for timestamp in batch)
