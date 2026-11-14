"""Simulated time with a unit, like 15min or 365d, for --step-size and --duration of the ecosim commands."""

import re
from argparse import ArgumentTypeError
from dataclasses import dataclass
from decimal import Decimal

from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.datetime.readable_duration import readable_duration

# m is not a unit, so 15m cannot be taken for minutes or months. y is 365 days.
MILLISECONDS_OF_UNIT = {"ms": 1, "s": 1_000, "min": 60_000, "h": 3_600_000, "d": 86_400_000, "y": 365 * 86_400_000}
DURATION_PATTERN = re.compile(r"(?P<number>\d+(\.\d+)?)\s*(?P<unit>[a-z]+)")


@dataclass(frozen=True)
class Duration:
    text: str
    milliseconds: int


def duration(text: str) -> Duration:
    """A converter for argparse: a number and one of the units, like 90min, 1.5h or 7d."""
    match = DURATION_PATTERN.fullmatch(text.strip())
    if match is None or match["unit"] not in MILLISECONDS_OF_UNIT:
        raise ArgumentTypeError(f"must be a number with one of the units ms, s, min, h, d or y, like 15min, not '{text}'")
    milliseconds = Decimal(match["number"]) * MILLISECONDS_OF_UNIT[match["unit"]]
    if milliseconds < 1 or milliseconds != milliseconds.to_integral_value():
        raise ArgumentTypeError(f"must be a whole number of milliseconds, at least 1 ms, not '{text}'")
    return Duration(text=text.strip(), milliseconds=int(milliseconds))


def step_size_in_milliseconds(text: str) -> int:
    """A duration, or milliseconds as for ecosim-server and setup.delta_t."""
    if text.strip().isdecimal():
        return ConfigParser.positive_whole_number(text)
    return duration(text).milliseconds


def steps_of_duration(run_duration: Duration, step_size_in_milliseconds: int, length_name: str = "--duration") -> int:
    steps, rest = divmod(run_duration.milliseconds, step_size_in_milliseconds)
    if rest == 0:
        return steps
    nearest = [
        f"--steps {count} ({readable_duration(seconds=count * step_size_in_milliseconds / 1000)})" for count in (steps, steps + 1) if count > 0
    ]
    step_size = readable_duration(seconds=step_size_in_milliseconds / 1000)
    raise ArgumentTypeError(f"{length_name} {run_duration.text} is not a whole number of steps of {step_size}. Use {' or '.join(nearest)}.")
