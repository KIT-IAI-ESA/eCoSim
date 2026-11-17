from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from ecosim_common.tech.datetime.readable_duration import readable_duration
from ecosim_server.config.simulation_config import SimulationConfig


@dataclass
class StepProgress:
    _simulation_config: SimulationConfig = field()
    _clock: Callable[[], float] = field(default=time.monotonic)
    first_step: int = field(init=False, default=0)
    _started_at: float = field(init=False, default=0.0)
    _last_line_at: float = field(init=False, default=0.0)
    _last_step_at: float | None = field(init=False, default=None)

    def start(self, first_step: int) -> None:
        self.first_step = first_step
        self._started_at = self._last_line_at = self._clock()

    def step_completed(self, completed_steps: int) -> str | None:
        """Returns the progress line if one is due."""
        self._last_step_at = now = self._clock()
        if completed_steps >= self._simulation_config.steps or now - self._last_line_at < self._interval_in_seconds():
            return None
        self._last_line_at = now
        return self._line(completed_steps=completed_steps, elapsed_in_seconds=now - self._started_at)

    def step_time_in_seconds(self) -> float | None:
        if self._last_step_at is None:
            return None
        return self._last_step_at - self._started_at

    def _interval_in_seconds(self) -> float:
        elapsed_at_last_line = self._last_line_at - self._started_at
        if elapsed_at_last_line < 60:
            return 10
        return 60 if elapsed_at_last_line < 3_600 else 600

    def _line(self, completed_steps: int, elapsed_in_seconds: float) -> str:
        steps = self._simulation_config.steps
        steps_per_second = (completed_steps - self.first_step) / elapsed_in_seconds
        return (
            f"Step {completed_steps:,} of {steps:,} ({completed_steps * 100 // steps} %), simulated {self._simulated_time(completed_steps)}, "
            f"{speed_text(steps_per_second)}, about {readable_duration((steps - completed_steps) / steps_per_second)} left"
        )

    def _simulated_time(self, completed_steps: int) -> str:
        time_format = "%Y-%m-%d %H:%M" if self._simulation_config.step_size_in_ms % 60_000 == 0 else "%Y-%m-%d %H:%M:%S"
        return self._simulation_config.date_time_for_step(step=completed_steps - 1).strftime(time_format)


def speed_text(steps_per_second: float) -> str:
    if steps_per_second >= 1:
        return f"{steps_per_second:,.0f} steps/s"
    return f"{readable_duration(1 / steps_per_second)} per step"
