from __future__ import annotations
import dataclasses
import threading
from typing import List, Tuple

from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
)
from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequestInputs
from ecosim_server.data.repositories import Repositories
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig


class InterfaceValueHistory:
    _logger = ESPLogger("InterfaceValueHistory")
    _default_values_marker = -1

    def __init__(
        self,
        repositories: Repositories,
        simulation_config: SimulationConfig,
    ):
        self.__thread_lock = threading.Lock()
        self._entries: dict[int, dict[ClientID, List[ProtocolInterfaceValue]]] = {}
        self._repositories = repositories
        self._simulation_config = simulation_config

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
        InterfaceValueHistory._logger.debug(
            f"Adding new entry: TimeStep: {time_step} - ClientID: {client_id} - values: {interface_values}",
        )
        with self.__thread_lock:
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

    def _add_to_entries_internal(
        self,
        time_step: int,
        client_id: ClientID,
        interface_values: Tuple[ProtocolInterfaceValue, ...],
    ) -> None:
        self._get_mutable_entry(
            time_step=time_step,
            client_id=client_id,
        ).extend(interface_values)

    def _get_mutable_entry(
        self,
        time_step: int,
        client_id: ClientID,
    ) -> List[ProtocolInterfaceValue]:
        if time_step not in self._entries:
            self._entries[time_step] = {}
        if client_id not in self._entries[time_step]:
            self._entries[time_step][client_id] = []
        return self._entries[time_step][client_id]

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
            InterfaceValueHistory._logger.debug(
                f"Initializing from repositories for client {client.client_id}",
            )
            client_repo = self._repositories.measurement_repository(
                client_id=client.client_id,
            )
            sorted_entries = sorted(client_repo.all(), key=lambda it: it.timestamp)
            InterfaceValueHistory._logger.debug(
                f"Initializing from repositories for client {client.client_id}: found {len(sorted_entries)} entries",
            )
            for entry in sorted_entries:
                step: int = self._simulation_config.date_time_to_step(entry.timestamp)
                self._add_to_entries_internal(step, client.client_id, entry.values)
            InterfaceValueHistory._logger.debug(
                f"Initializing from repositories for client {client.client_id}: successfully restored {len(sorted_entries)} entries",
            )

    def contains_all_default_values(self) -> bool:
        return (
            InterfaceValueHistory._default_values_marker in self._entries.keys() and
            self._entries[InterfaceValueHistory._default_values_marker].keys() == {
                client.client_id for client in self._simulation_config.clients
            }
        )

    def calculate_current_execution_step_or_exception(self) -> RestoreData:
        InterfaceValueHistory._logger.debug("Calculating current execution step...")
        latest_completed_step_by_client: dict[ClientID, int] = dict[ClientID, int]()
        latest_step: int = self._get_latest_timestep()
        second_latest_timestep: int = latest_step - 1 if latest_step > 0 else 0
        clients_with_missing_steps: List[ClientID] = []
        for client in self._simulation_config.clients:
            if len(self._entries.keys()) == 0:
                InterfaceValueHistory._logger.debug("No entries in self._entries -> skipping any calculation")
                latest_completed_step_by_client[client.client_id] = -1
                continue
            latest_step_for_client = latest_step
            if client.client_id not in self._entries[latest_step].keys():
                if client.client_id not in self._entries[second_latest_timestep].keys():
                    clients_with_missing_steps.append(client.client_id)
                    continue
                latest_step_for_client = second_latest_timestep
            client_interfaces = [interface.name for interface in self._entries[latest_step_for_client][client.client_id]]
            latest_completed_step_by_client[client.client_id] = latest_step_for_client
            for interface in client.interfaces:
                if interface.name not in client_interfaces:
                    latest_completed_step_by_client[client.client_id] = second_latest_timestep
                    break
        if len(clients_with_missing_steps) > 0:
            raise RuntimeError(
                f"Cannot calculate current execution step because some clients are missing steps: {clients_with_missing_steps}",
            )
        restore_data = RestoreData.of(
            latest_completed_step_by_client=latest_completed_step_by_client,
            repositories=self._repositories,
        )
        InterfaceValueHistory._logger.debug(f"Calculating current execution step... finished. restore_data={restore_data}")
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


@dataclasses.dataclass(frozen=True)
class RestoreData:
    current_step: int
    client_restore_data: dict[ClientID, SimulationStepBatchRequestInputs]

    @staticmethod
    def of(
        latest_completed_step_by_client: dict[ClientID, int],
        repositories: Repositories,
    ) -> RestoreData:
        return RestoreData(
            current_step=min(latest_completed_step_by_client.values()) + 1,  # the step after the latest min completed step needs to be executed
            client_restore_data=RestoreData._transform_history_to_restore_data(
                latest_completed_step_by_client=latest_completed_step_by_client,
                repositories=repositories,
            ),
        )

    @staticmethod
    def _transform_history_to_restore_data(
        latest_completed_step_by_client: dict[ClientID, int],
        repositories: Repositories,
    ) -> dict[ClientID, SimulationStepBatchRequestInputs]:
        result: dict[ClientID, SimulationStepBatchRequestInputs] = {}
        for client_id, latest_completed_step in latest_completed_step_by_client.items():
            client_repository = repositories.measurement_repository(client_id)
            all_entries = client_repository.all()
            transformed_entries: SimulationStepBatchRequestInputs = {entry.timestamp: list(entry.values) for entry in all_entries}
            result[client_id] = transformed_entries
        return result
