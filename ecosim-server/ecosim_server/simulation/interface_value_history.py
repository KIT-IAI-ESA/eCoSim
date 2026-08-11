from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
)
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequestInputs
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories


@dataclass
class InterfaceValueHistory:
    logger = ESPLogger("InterfaceValueHistory")
    _default_values_marker = -1

    _repositories: Repositories = field()
    _simulation_config: SimulationConfig = field()
    _entries: ESPMap[int, dict[ClientID, List[ProtocolInterfaceValue]]] = field()

    @staticmethod
    def for_config(
        repositories: Repositories,
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
    ) -> InterfaceValueHistory:
        return InterfaceValueHistory(
            _repositories=repositories,
            _simulation_config=simulation_config,
            # _entries=ESPMap.of_type(
            #     map_type=ESPStructureType.DASK_VARIABLE
            #     if server_config.server.communication_protocol == CommunicationProtocol.DASK
            #     else ESPStructureType.THREAD,
            # ),
            _entries=ESPMap.of_type(
                map_type=ESPStructureType.THREAD,
            ),
        )

    def add_default_values(
        self,
        client_id: ClientID,
        client_sim_step_data: ClientSimStepData,
    ) -> None:
        self.add(
            InterfaceValueHistory._default_values_marker,
            client_id,
            tuple(client_sim_step_data.interface_values),
        )

    def add(
        self,
        time_step: int,
        client_id: ClientID,
        interface_values: Tuple[ProtocolInterfaceValue, ...],
    ) -> None:
        # TODO_OSR: let adding code run in own thread
        InterfaceValueHistory.logger.debug("Adding new entry: TimeStep: %s - ClientID: %s - values: %s ...", time_step, client_id, interface_values)
        self._add_to_entries_internal(
            time_step=time_step,
            client_id=client_id,
            interface_values=interface_values,
        )
        self._add_to_repository_internal(
            step=time_step,
            client_id=client_id,
            values=interface_values,
        )
        InterfaceValueHistory.logger.debug(
            "Adding new entry: TimeStep: %s - ClientID: %s - values: %s ... done.",
            time_step,
            client_id,
            interface_values,
        )

    def _add_to_entries_internal(
        self,
        time_step: int,
        client_id: ClientID,
        interface_values: Tuple[ProtocolInterfaceValue, ...],
    ) -> None:
        with self._entries.transaction() as entries:
            if time_step not in entries:
                entries[time_step] = {}
            if client_id not in entries[time_step]:
                entries[time_step][client_id] = []
            entries[time_step][client_id].extend(interface_values)

    def _add_to_repository_internal(
        self,
        step: int,
        client_id: ClientID,
        values: Tuple[ProtocolInterfaceValue, ...],
    ) -> None:
        if step != InterfaceValueHistory._default_values_marker:
            self._repositories.measurement_repository(client_id).add(
                values=values,
                timestamp=self._simulation_config.date_time_for_step(step),
            )

    def init_from_repositories(self) -> None:
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
            InterfaceValueHistory.logger.debug(
                "Initializing from repositories for client %s: found %s entries",
                client.client_id,
                len(sorted_entries),
            )
            for entry in sorted_entries:
                step: int = self._simulation_config.date_time_to_step(entry.timestamp)
                self._add_to_entries_internal(step, client.client_id, entry.values)
            InterfaceValueHistory.logger.debug(
                "Initializing from repositories for client %s: successfully restored %s entries",
                client.client_id,
                len(sorted_entries),
            )

    def contains_all_default_values(self) -> bool:
        return InterfaceValueHistory._default_values_marker in self._entries.keys() and self._entries[
            InterfaceValueHistory._default_values_marker
        ].keys() == {client.client_id for client in self._simulation_config.clients}

    def calculate_current_execution_step_or_exception(self) -> RestoreData:
        InterfaceValueHistory.logger.debug("Calculating current execution step...")
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


class InterfaceValueHistoryEntry:
    def __init__(
        self,
        time_step: float,
        interface_values: List[ProtocolInterfaceValue],
    ):
        self.time = time_step
        self.interface_values = interface_values


@dataclass(frozen=True)
class RestoreData:
    current_step: int
    client_restore_data: dict[ClientID, SimulationStepBatchRequestInputs]

    @staticmethod
    def of(
        latest_completed_step_by_client: dict[ClientID, int],
        repositories: Repositories,
    ) -> RestoreData:
        common_latest_completed_step = min(latest_completed_step_by_client.values())
        return RestoreData(
            current_step=common_latest_completed_step + 1,  # the step after the latest min completed step needs to be executed
            client_restore_data=RestoreData._transform_history_to_restore_data(
                common_latest_completed_step=common_latest_completed_step,
                latest_completed_step_by_client=latest_completed_step_by_client,
                repositories=repositories,
            ),
        )

    @staticmethod
    def _transform_history_to_restore_data(
        common_latest_completed_step: int,
        latest_completed_step_by_client: dict[ClientID, int],
        repositories: Repositories,
    ) -> dict[ClientID, SimulationStepBatchRequestInputs]:
        result: dict[ClientID, SimulationStepBatchRequestInputs] = {}
        for client_id, latest_completed_step_client in latest_completed_step_by_client.items():
            client_repository = repositories.measurement_repository(client_id)
            all_entries = sorted(client_repository.all(), key=lambda it: it.timestamp)
            too_many_entries = latest_completed_step_client - common_latest_completed_step
            for i in range(too_many_entries):
                all_entries.pop()
            InterfaceValueHistory.logger.debug("Transforming history to restore data for client %s: found %s entries", client_id, len(all_entries))
            transformed_entries: SimulationStepBatchRequestInputs = {entry.timestamp: list(entry.values) for entry in all_entries}
            result[client_id] = transformed_entries
        return result
