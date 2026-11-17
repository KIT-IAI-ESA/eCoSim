from __future__ import annotations

from dataclasses import dataclass

from ecosim_common.tech.datetime.readable_duration import readable_duration
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_server.config.server_config import DatabaseConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.simulation.step_progress import speed_text


@dataclass(frozen=True)
class RunSummary:
    failure_reason: str | None
    completed_steps: int
    restored_steps: int
    step_time_in_seconds: float | None
    simulation_config: SimulationConfig
    database: DatabaseConfig

    def print_to_info(self) -> None:
        GlobalLogger.print_values(header=self.header(), value_pairs=self.value_pairs())

    def header(self) -> str:
        return "SIMULATION FINISHED" if self.failure_reason is None else "SIMULATION FAILED"

    def value_pairs(self) -> dict[str, str]:
        has_results = self.completed_steps > 0
        value_pairs = {
            "Steps": self._steps_text(),
            "Simulated period": self.simulation_config.simulated_period_text(completed_steps=self.completed_steps) if has_results else None,
            "Reason": self.failure_reason,
            "Results": self.database.results_location() if has_results else None,
            "Continue the run": (
                "start the server again with the same options and --restore-simulation-run, then the clients"
                if self.failure_reason is not None and has_results
                else None
            ),
        }
        return {key: value for key, value in value_pairs.items() if value is not None}

    def _steps_text(self) -> str:
        text = f"{self.completed_steps:,} of {self.simulation_config.steps:,}"
        if self.restored_steps > 0:
            text += f", {self.restored_steps:,} of them restored"
        steps_of_this_run = self.completed_steps - self.restored_steps
        if not self.step_time_in_seconds or steps_of_this_run == 0:
            return text
        return f"{text}, in {readable_duration(self.step_time_in_seconds)} ({speed_text(steps_of_this_run / self.step_time_in_seconds)})"
