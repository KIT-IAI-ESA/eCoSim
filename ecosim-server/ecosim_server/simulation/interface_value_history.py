from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Tuple

from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
)
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.simulation.interface_value_history_thread import (
    DEFAULT_VALUES_MARKER,
    InterfaceValueHistoryEntries,
    InterfaceValueHistoryEntry,
    InterfaceValueHistoryThread,
    add_to_entries,
)
from ecosim_server.simulation.restore_data import RestoreData


@dataclass
class InterfaceValueHistory:
    logger = ESPLogger("InterfaceValueHistory")

    _repositories: Repositories = field()
    _simulation_config: SimulationConfig = field()
    _entries: InterfaceValueHistoryEntries = field()
    _entries_queue: ESPQueue[InterfaceValueHistoryEntry] = field()
    _adding_thread: InterfaceValueHistoryThread = field(init=False)

    @staticmethod
    def for_config(
        repositories: Repositories,
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
    ) -> InterfaceValueHistory:
        return InterfaceValueHistory(
            _repositories=repositories,
            _simulation_config=simulation_config,
            _entries=ESPMap.of_type(
                map_type=ESPStructureType.THREAD,
            ),
            _entries_queue=ESPQueue.of_communication_protocol(
                communication_protocol=server_config.server.communication_protocol,
            ),
        )

    def __post_init__(self) -> None:
        self._adding_thread = self._create_adding_thread()
        self._adding_thread.start()

    def __getstate__(self) -> dict[str, Any]:
        return {
            "_repositories": self._repositories,
            "_simulation_config": self._simulation_config,
            "_entries": self._entries,
            "_entries_queue": self._entries_queue,
        }

    def __setstate__(self, state: dict[str, Any]) -> None:
        # the thread is not started again - it stays in the process that created the history
        self.__dict__.update(state)
        self._adding_thread = self._create_adding_thread()

    def _create_adding_thread(self) -> InterfaceValueHistoryThread:
        return InterfaceValueHistoryThread(
            _entries_queue=self._entries_queue,
            _entries=self._entries,
            _repositories=self._repositories,
            _simulation_config=self._simulation_config,
        )

    def add_default_values(
        self,
        client_id: ClientID,
        client_sim_step_data: ClientSimStepData,
    ) -> None:
        self.add(
            DEFAULT_VALUES_MARKER,
            client_id,
            tuple(client_sim_step_data.interface_values),
        )

    def add(
        self,
        time_step: int,
        client_id: ClientID,
        interface_values: Tuple[ProtocolInterfaceValue, ...],
    ) -> None:
        """Pushes the entry into the queue - the adding thread adds it to the entries and to the repositories."""
        InterfaceValueHistory.logger.debug("Adding new entry: TimeStep: %s - ClientID: %s - values: %s ...", time_step, client_id, interface_values)
        self._entries_queue.push(
            InterfaceValueHistoryEntry(
                time_step=time_step,
                client_id=client_id,
                interface_values=interface_values,
            ),
        )

    def flush(self) -> None:
        """Waits until every entry pushed so far is added."""
        self._adding_thread.flush()

    def close(self) -> None:
        """Adds the remaining entries and stops the adding thread."""
        self._adding_thread.close()

    def init_from_repositories(self) -> None:
        self.flush()  # the entries and the repositories are read below - so as a precaution the 'flush' method is called
        if len(self._entries.values()) > 0:
            raise RuntimeError(
                "Cannot init from repositories because there are already entries.",
            )
        for client in self._simulation_config.clients:
            InterfaceValueHistory.logger.debug("Initializing from repositories for client %s", client.client_id)
            client_repo = self._repositories.measurement_repository(
                client_id=client.client_id,
            )
            sorted_entries = sorted(client_repo.all(), key=lambda it: it.timestamp)
            if InterfaceValueHistory.logger.is_debug_enabled:
                InterfaceValueHistory.logger.debug(
                    "Initializing from repositories for client %s: found %s entries",
                    client.client_id,
                    len(sorted_entries),
                )
            for entry in sorted_entries:
                step: int = self._simulation_config.date_time_to_step(entry.timestamp)
                # the entries come from the repositories, so they are added directly and not through the queue
                add_to_entries(
                    self._entries,
                    InterfaceValueHistoryEntry(
                        time_step=step,
                        client_id=client.client_id,
                        interface_values=entry.values,
                    ),
                )
            if InterfaceValueHistory.logger.is_debug_enabled:
                InterfaceValueHistory.logger.debug(
                    "Initializing from repositories for client %s: successfully restored %s entries",
                    client.client_id,
                    len(sorted_entries),
                )

    def contains_all_default_values(self) -> bool:
        self.flush()  # the entries are read below - so as a precaution, the 'flush' method is called
        return DEFAULT_VALUES_MARKER in self._entries.keys() and self._entries[DEFAULT_VALUES_MARKER].keys() == {
            client.client_id for client in self._simulation_config.clients
        }

    def calculate_restore_data_or_exception(self) -> RestoreData:
        InterfaceValueHistory.logger.debug("Calculating current execution step...")
        self.flush()  # the entries and (through 'RestoreData') the repositories are read below
        restore_data = RestoreData.of(
            latest_completed_step_by_client={client.client_id: self._latest_completed_step(client) for client in self._simulation_config.clients},
            repositories=self._repositories,
            simulation_config=self._simulation_config,
        )
        InterfaceValueHistory.logger.debug("Calculating current execution step... finished. restore_data=%s", restore_data)
        return restore_data

    def _latest_completed_step(self, client: ClientSimulatorConfig) -> int:
        """The last step whose row has every interface of the client, -1 if there is none."""
        interface_names = {interface.name for interface in client.interfaces}
        completed_steps = [
            step
            for step, values_by_client in self._entries.items()
            if client.client_id in values_by_client and interface_names <= {value.name for value in values_by_client[client.client_id]}
        ]
        return max(completed_steps, default=-1)

    def remove_steps_starting_at(self, step: int) -> None:
        """Removes the stored rows of every client from this step on, so a step that runs again is not stored twice."""
        # a write still on its way would bring a removed row back
        self.flush()
        timestamp = self._simulation_config.date_time_for_step(step)
        for client in self._simulation_config.clients:
            self._repositories.measurement_repository(client_id=client.client_id).remove_starting_at(timestamp=timestamp)
