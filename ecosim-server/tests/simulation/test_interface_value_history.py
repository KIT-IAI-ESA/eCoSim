from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass, field
from typing import List, Tuple, cast, override

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_server.simulation.interface_value_history import InterfaceValueHistory
from ecosim_server.simulation.interface_value_history_thread import InterfaceValueHistoryThread
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository
from tests.tech.resource_utils import resource_path_file

_TIMEOUT_IN_SECONDS = 10.0


class RecordingMeasurementRepository(MeasurementRepository):
    """Records every added measurement together with the thread that added it."""

    def __init__(self) -> None:
        self.entries: List[MeasurementEntry] = []
        self.adding_thread_ids: List[int] = []
        self.blocker = threading.Event()
        self.add_started = threading.Event()
        self.failure: Exception | None = None
        self._lock = threading.Lock()

    @override
    def add(
        self,
        values: Tuple[ProtocolInterfaceValue, ...],
        timestamp: datetime.datetime,
    ) -> None:
        self.add_started.set()
        self.blocker.wait(timeout=_TIMEOUT_IN_SECONDS)
        if self.failure is not None:
            raise self.failure
        with self._lock:
            self.adding_thread_ids.append(threading.get_ident())
            self.entries.append(MeasurementEntry(values=values, timestamp=timestamp))

    @override
    def all(self) -> List[MeasurementEntry]:
        with self._lock:
            return list(self.entries)


@dataclass(frozen=True)
class RecordingRepositories(Repositories):
    _repository_by_client: dict[ClientID, RecordingMeasurementRepository] = field(default_factory=dict)
    simulation_state_repository: SimulationStateRepository = field(default=cast(SimulationStateRepository, None))
    server_time_measurement_repository: ServerTimeMeasurementRepository = field(default=cast(ServerTimeMeasurementRepository, None))

    @override
    def measurement_repository(
        self,
        client_id: ClientID,
    ) -> RecordingMeasurementRepository:
        if client_id not in self._repository_by_client:
            self._repository_by_client[client_id] = RecordingMeasurementRepository()
        return self._repository_by_client[client_id]


def _client_id() -> ClientID:
    return ClientID(model_name="weather", simulator_name="weather")


def _values(value: float = 1.0) -> Tuple[ProtocolInterfaceValue, ...]:
    return (ProtocolInterfaceValue(name="T_out", value=value),)


def _client_sim_step_data() -> ClientSimStepData:
    return ClientSimStepData(interface_values=list(_values()))


def _simulation_config() -> SimulationConfig:
    return SimulationConfig.of_config_file_and_params(resource_path_file("simulation.json"), 100)


def _history(
    repositories: RecordingRepositories,
    communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
    blocked: bool = False,
) -> InterfaceValueHistory:
    if not blocked:
        repositories.measurement_repository(_client_id()).blocker.set()
    return InterfaceValueHistory(
        _repositories=repositories,
        _simulation_config=_simulation_config(),
        _entries=ESPMap.of_type(ESPStructureType.THREAD),
        _entries_queue=ESPQueue.of_communication_protocol(communication_protocol),
    )


def test_add_adds_the_entry_in_an_own_thread(communication_protocol: CommunicationProtocol) -> None:
    repositories = RecordingRepositories()
    history = _history(repositories, communication_protocol)

    history.add(time_step=0, client_id=_client_id(), interface_values=_values())
    history.close()

    repository = repositories.measurement_repository(_client_id())
    assert [entry.values for entry in repository.all()] == [_values()]
    assert repository.adding_thread_ids != [threading.get_ident()]


def test_add_does_not_wait_for_the_entry_to_be_added() -> None:
    repositories = RecordingRepositories()
    history = _history(repositories, blocked=True)
    repository = repositories.measurement_repository(_client_id())

    history.add(time_step=0, client_id=_client_id(), interface_values=_values())

    assert repository.add_started.wait(timeout=_TIMEOUT_IN_SECONDS), "the adding thread did not start"
    assert repository.all() == [], "'add' returned only after the entry was added"
    repository.blocker.set()
    history.close()
    assert len(repository.all()) == 1


def test_the_entries_are_added_in_the_order_they_were_handed_over() -> None:
    repositories = RecordingRepositories()
    history = _history(repositories)

    for step in range(100):
        history.add(time_step=step, client_id=_client_id(), interface_values=_values(float(step)))
    history.close()

    assert [entry.values for entry in repositories.measurement_repository(_client_id()).all()] == [_values(float(step)) for step in range(100)]


def test_a_reader_sees_the_entries_that_are_still_on_their_way() -> None:
    repositories = RecordingRepositories()
    history = _history(repositories)

    for client in _simulation_config().clients:
        history.add_default_values(client_id=client.client_id, client_sim_step_data=_client_sim_step_data())

    assert history.contains_all_default_values(), "the reader did not wait for the entries of the adding thread"
    history.close()


def test_the_default_values_are_not_added_to_the_repository() -> None:
    repositories = RecordingRepositories()
    history = _history(repositories)

    history.add_default_values(client_id=_client_id(), client_sim_step_data=_client_sim_step_data())
    history.close()

    assert repositories.measurement_repository(_client_id()).all() == []


def test_flush_raises_if_an_entry_could_not_be_added() -> None:
    repositories = RecordingRepositories()
    history = _history(repositories)
    repositories.measurement_repository(_client_id()).failure = RuntimeError("db is gone")

    history.add(time_step=0, client_id=_client_id(), interface_values=_values())

    with pytest.raises(RuntimeError):
        history.flush()
    history.close()


def test_close_stops_the_adding_thread() -> None:
    repositories = RecordingRepositories()
    threads_before = _adding_threads()
    history = _history(repositories)

    history.add(time_step=0, client_id=_client_id(), interface_values=_values())
    history.close()

    assert _adding_threads() == threads_before
    assert len(repositories.measurement_repository(_client_id()).all()) == 1


def _adding_threads() -> set[threading.Thread]:
    return {thread for thread in threading.enumerate() if thread.name == InterfaceValueHistoryThread.THREAD_NAME}
