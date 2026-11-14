from __future__ import annotations

import argparse
from argparse import ArgumentTypeError
from dataclasses import dataclass
from datetime import UTC, datetime

from ecosim.report_lines import and_joined
from ecosim.run_length import duration, step_size_in_milliseconds, steps_of_duration

DEFAULT_STEP_SIZE = "15min"
DEFAULT_DURATION = "1d"
DEFAULT_START_DATE = "2024-01-01"


@dataclass(frozen=True)
class SimulationLength:
    """The setup of the new simulation, and which of its values are defaults."""

    step_size_in_milliseconds: int
    steps: int
    start_date: datetime
    # like "the step size 15min", with the option that changes it
    defaults: tuple[tuple[str, str], ...]

    @staticmethod
    def of_options(options: argparse.Namespace) -> SimulationLength:
        """Raises ArgumentTypeError for a duration that is not a whole number of steps."""
        step_size = options.step_size or step_size_in_milliseconds(text=DEFAULT_STEP_SIZE)
        run_duration = options.duration or duration(text=DEFAULT_DURATION)
        length_name = "--duration" if options.duration else "The default length"
        return SimulationLength(
            step_size_in_milliseconds=step_size,
            steps=options.steps or steps_of_duration(run_duration=run_duration, step_size_in_milliseconds=step_size, length_name=length_name),
            start_date=options.start_date or start_date(text=DEFAULT_START_DATE),
            defaults=_defaults_of(options=options),
        )

    def defaults_line(self) -> str | None:
        """Like 'The step size 15min is the default. Choose another with --step-size.'"""
        if not self.defaults:
            return None
        values = and_joined(texts=[value for value, _ in self.defaults])
        options = and_joined(texts=[option for _, option in self.defaults])
        if len(self.defaults) == 1:
            return f"{values[0].upper()}{values[1:]} is the default. Choose another with {options}."
        return f"{values[0].upper()}{values[1:]} are the defaults. Choose others with {options}."


def _defaults_of(options: argparse.Namespace) -> tuple[tuple[str, str], ...]:
    defaults = []
    if options.step_size is None:
        defaults.append((f"the step size {DEFAULT_STEP_SIZE}", "--step-size"))
    if options.steps is None and options.duration is None:
        defaults.append((f"the length {DEFAULT_DURATION}", "--duration"))
    if options.start_date is None:
        defaults.append((f"the start date {DEFAULT_START_DATE}", "--start-date"))
    return tuple(defaults)


def start_date(text: str) -> datetime:
    """A converter for argparse: an ISO date, or a date and a time, which is UTC without an offset."""
    try:
        moment = datetime.fromisoformat(text.strip())
    except ValueError:
        raise ArgumentTypeError(f"must be a date like 2023-01-01 or 2023-01-01T06:00+01:00, not '{text}'") from None
    return moment if moment.utcoffset() is not None else moment.replace(tzinfo=UTC)
