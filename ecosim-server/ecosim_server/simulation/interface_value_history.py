from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Tuple

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
from ecosim_server.config.simulation_config import SimulationConfig
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
        latest_completed_step_by_client: dict[ClientID, int] = dict[ClientID, int]()
        latest_step: int = self._get_latest_timestep()
        clients_with_missing_steps: List[ClientID] = []
        for client in self._simulation_config.clients:
            if len(self._entries.keys()) == 0:
                InterfaceValueHistory.logger.debug("No entries in self._entries -> skipping any calculation")
                latest_completed_step_by_client[client.client_id] = -1
                continue
            latest_step_for_client = latest_step
            if client.client_id not in self._entries[latest_step].keys():
                found_latest_step_for_client: bool = False
                while latest_step_for_client > 0 and not found_latest_step_for_client:
                    latest_step_for_client -= 1
                    if client.client_id not in self._entries[latest_step_for_client].keys():
                        continue
                    found_latest_step_for_client = True
                if not found_latest_step_for_client:
                    clients_with_missing_steps.append(client.client_id)
                    continue
            client_interfaces = [interface.name for interface in self._entries[latest_step_for_client][client.client_id]]
            latest_completed_step_by_client[client.client_id] = latest_step_for_client
            # check if all interfaces are present -> otherwise it is an uncompleted step
            for interface in client.interfaces:
                if interface.name not in client_interfaces:
                    latest_completed_step_by_client[client.client_id] = latest_step_for_client - 1
                    break
        if len(clients_with_missing_steps) > 0:
            raise RuntimeError(
                f"Cannot calculate current execution step because some clients are missing steps: {clients_with_missing_steps}",
            )
        restore_data = RestoreData.of(
            latest_completed_step_by_client=latest_completed_step_by_client,
            repositories=self._repositories,
        )
        InterfaceValueHistory.logger.debug("Calculating current execution step... finished. restore_data=%s", restore_data)
        return restore_data

    def _get_latest_timestep(self) -> int:
        if not self._entries:
            return 0
        return max(self._entries.keys())  # the keys are the steps, so they range from 0 to the latest step
