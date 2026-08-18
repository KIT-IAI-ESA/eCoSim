from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ecosim_common.communication.data.simulation_step_batch_request import SimulationStepBatchRequestInputs
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
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
            if RestoreData._logger.is_debug_enabled:
                RestoreData._logger.debug(
                    "Transforming history to restore data for client %s: found %s entries",
                    client_id,
                    len(all_entries),
                )
            transformed_entries: SimulationStepBatchRequestInputs = {entry.timestamp: list(entry.values) for entry in all_entries}
            result[client_id] = transformed_entries
        return result
