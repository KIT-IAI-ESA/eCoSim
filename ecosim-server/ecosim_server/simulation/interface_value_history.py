import datetime
import threading
from typing import List, Tuple

from ecosim_common.communication.data.client_sim_step_data import ClientSimStepData
from ecosim_common.communication.data.protocol_interface_value import (
    ProtocolInterfaceValue,
)
from ecosim_server.data.repositories import Repositories
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig


class InterfaceValueHistory:
    _logger = ESPLogger("InterfaceValueHistory")
    _default_values_marker = -1.0

    def __init__(
        self,
        repositories: Repositories,
        simulation_config: SimulationConfig,
    ):
        self.__thread_lock = threading.Lock()
        self._entries: dict[float, dict[ClientID, List[ProtocolInterfaceValue]]] = {}
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
        time_step: float,
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
                time_step=time_step,
                client_id=client_id,
                values=interface_values,
            )

    def _add_to_entries_internal(
        self,
        time_step: float,
        client_id: ClientID,
        interface_values: Tuple[ProtocolInterfaceValue, ...],
    ) -> None:
        if time_step not in self._entries:
            self._entries[time_step] = {}
        if client_id not in self._entries[time_step]:
            self._entries[time_step][client_id] = []
        self._entries[time_step][client_id].extend(interface_values)

    def _add_to_repository_internal(
        self,
        time_step: float,
        client_id: ClientID,
        values: Tuple[ProtocolInterfaceValue, ...],
    ) -> None:
        if time_step != InterfaceValueHistory._default_values_marker:
            self._repositories.measurement_repository(client_id).add(
                values=values,
                timestamp=self._simulation_config.date_time_for_step(
                    time_step,
                ),
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
                step = self._timestamp_to_step(entry.timestamp)
                self._add_to_entries_internal(step, client.client_id, entry.values)
            InterfaceValueHistory._logger.debug(
                f"Initializing from repositories for client {client.client_id}: successfully restored {len(sorted_entries)} entries",
            )

    def _timestamp_to_step(
        self,
        timestamp: datetime.datetime,
    ) -> float:
        passed_milliseconds = (
            timestamp.timestamp() * 1000
            - self._simulation_config.start_date.timestamp() * 1000
        )
        plausibility_check = (
            passed_milliseconds % self._simulation_config.step_size_in_ms
        ) == 0
        if not plausibility_check:
            raise RuntimeError(f"Timestamp {timestamp} is not a plausible step time.")
        return passed_milliseconds / self._simulation_config.step_size_in_ms


class InterfaceValueHistoryEntry:
    def __init__(
        self,
        time_step: float,
        interface_values: List[ProtocolInterfaceValue],
    ):
        self.time = time_step
        self.interface_values = interface_values
