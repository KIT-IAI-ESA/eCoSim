from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Iterable

from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequestInputs
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories


@dataclass(frozen=True)
class RestoreData:
    _logger: ClassVar[ESPLogger] = ESPLogger("RestoreData")

    current_step: int
    client_restore_data: dict[ClientID, SimulationStepBatchRequestInputs]

    @staticmethod
    def of(
        latest_completed_step_by_client: dict[ClientID, int],
        repositories: Repositories,
        simulation_config: SimulationConfig,
    ) -> RestoreData:
        common_latest_completed_step = min(latest_completed_step_by_client.values())
        return RestoreData(
            current_step=common_latest_completed_step + 1,  # the step after the latest min completed step needs to be executed
            client_restore_data=RestoreData._transform_history_to_restore_data(
                common_latest_completed_step=common_latest_completed_step,
                client_ids=latest_completed_step_by_client.keys(),
                repositories=repositories,
                simulation_config=simulation_config,
            ),
        )

    @staticmethod
    def _transform_history_to_restore_data(
        common_latest_completed_step: int,
        client_ids: Iterable[ClientID],
        repositories: Repositories,
        simulation_config: SimulationConfig,
    ) -> dict[ClientID, SimulationStepBatchRequestInputs]:
        result: dict[ClientID, SimulationStepBatchRequestInputs] = {}
        for client_id in client_ids:
            client_repository = repositories.measurement_repository(client_id)
            all_entries = sorted(client_repository.all(), key=lambda it: it.timestamp)
            completed_entries = [
                entry for entry in all_entries if simulation_config.date_time_to_step(entry.timestamp) <= common_latest_completed_step
            ]
            if RestoreData._logger.is_debug_enabled:
                RestoreData._logger.debug(
                    "Transforming history to restore data for client %s: found %s entries",
                    client_id,
                    len(completed_entries),
                )
            transformed_entries: SimulationStepBatchRequestInputs = {entry.timestamp: list(entry.values) for entry in completed_entries}
            result[client_id] = transformed_entries
        return result
