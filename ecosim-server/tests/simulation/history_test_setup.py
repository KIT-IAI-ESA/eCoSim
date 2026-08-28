"""Shared setup for the 'InterfaceValueHistory' tests."""

from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass, field
from typing import List, Tuple, cast, override

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
from ecosim_server.simulation.interface_value_history_thread import InterfaceValueHistoryEntry
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository
from ecosim_test_common.resources.config_files import config_file_path

TIMEOUT_IN_SECONDS = 10.0


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
        self.blocker.wait(timeout=TIMEOUT_IN_SECONDS)
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


def values(value: float = 1.0) -> Tuple[ProtocolInterfaceValue, ...]:
    return (ProtocolInterfaceValue(name="T_out", value=value),)


def client_sim_step_data() -> ClientSimStepData:
    return ClientSimStepData(interface_values=list(values()))


def simulation_config() -> SimulationConfig:
    return SimulationConfig.of_config_file_and_params(config_file_path("simulation.json"), 100)


def history(
    repositories: RecordingRepositories,
    client_id: ClientID | None,
    communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
    blocked: bool = False,
    entries_queue: ESPQueue[InterfaceValueHistoryEntry] | None = None,
) -> InterfaceValueHistory:
    if not blocked and client_id is not None:
        repositories.measurement_repository(client_id).blocker.set()
    return InterfaceValueHistory(
        _repositories=repositories,
        _simulation_config=simulation_config(),
        _entries=ESPMap.of_type(ESPStructureType.THREAD),
        # explicitly against None: an empty 'ESPQueue' is falsy, so 'or' would discard it
        _entries_queue=entries_queue if entries_queue is not None else ESPQueue.of_communication_protocol(communication_protocol),
    )
