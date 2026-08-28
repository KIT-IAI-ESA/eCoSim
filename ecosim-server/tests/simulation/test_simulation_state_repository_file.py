from __future__ import annotations

import distributed
import pickle
from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository_file import SimulationStateRepositoryFile


def create_repository(
    directory: Path,
    communication_protocol: CommunicationProtocol,
) -> SimulationStateRepositoryFile:
    return SimulationStateRepositoryFile.create(
        directory=directory,
        communication_protocol=communication_protocol,
    )


def test_the_state_is_not_ready_before_the_first_update(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    assert (
        create_repository(
            tmp_path,
            communication_protocol=communication_protocol,
        ).current()
        is SimulationState.NOT_READY
    )


def test_the_updated_state_is_the_current_one(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(
        tmp_path,
        communication_protocol=communication_protocol,
    )

    repository.update(SimulationState.STARTED)

    assert repository.current() is SimulationState.STARTED


def test_the_last_update_wins(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(
        tmp_path,
        communication_protocol=communication_protocol,
    )

    repository.update(SimulationState.READY)
    repository.update(SimulationState.STARTED)
    repository.update(SimulationState.FINISHED)

    assert repository.current() is SimulationState.FINISHED


def test_the_state_is_persisted_for_a_new_repository_instance(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    create_repository(
        tmp_path,
        communication_protocol=communication_protocol,
    ).update(SimulationState.FAILED)

    assert (
        create_repository(
            tmp_path,
            communication_protocol=communication_protocol,
        ).current()
        is SimulationState.FAILED
    )


def test_the_repository_survives_a_pickle_round_trip(
    tmp_path: Path,
    dask_client: distributed.Client,
) -> None:
    repository = create_repository(tmp_path, communication_protocol=CommunicationProtocol.DASK)
    repository.update(SimulationState.STARTED)

    restored = pickle.loads(pickle.dumps(repository))

    assert restored.current() is SimulationState.STARTED
