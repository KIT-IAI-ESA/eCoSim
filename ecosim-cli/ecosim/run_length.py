import re
from argparse import ArgumentTypeError
from dataclasses import dataclass
from decimal import Decimal

from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.datetime.readable_duration import readable_duration

# m is left out, it could be minutes or months
MILLISECONDS_OF_UNIT = {"ms": 1, "s": 1_000, "min": 60_000, "h": 3_600_000, "d": 86_400_000, "y": 365 * 86_400_000}


@dataclass(frozen=True)
class Duration:
    text: str
    milliseconds: int


def duration(text: str) -> Duration:
    match = re.fullmatch(pattern=r"(?P<number>\d+(\.\d+)?)\s*(?P<unit>[a-z]+)", string=text.strip())
    if match is None or match["unit"] not in MILLISECONDS_OF_UNIT:
        raise ArgumentTypeError(f"must be a number with one of the units ms, s, min, h, d or y, like 15min, not '{text}'")
    milliseconds = Decimal(match["number"]) * MILLISECONDS_OF_UNIT[match["unit"]]
    if milliseconds < 1 or milliseconds != milliseconds.to_integral_value():
        raise ArgumentTypeError(f"must be a whole number of milliseconds, at least 1 ms, not '{text}'")
    return Duration(text=text.strip(), milliseconds=int(milliseconds))


def step_size_in_ms(text: str) -> int:
    if text.strip().isdecimal():
        return ConfigParser.positive_whole_number(text)
    return duration(text=text).milliseconds


def steps_of_duration(run_duration: Duration, step_size_in_ms: int, length_name: str = "--duration") -> int:
    steps, rest = divmod(run_duration.milliseconds, step_size_in_ms)
    if rest == 0:
        return steps
    nearest = [f"--steps {count} ({readable_duration(seconds=count * step_size_in_ms / 1000)})" for count in (steps, steps + 1) if count > 0]
    step_size = readable_duration(seconds=step_size_in_ms / 1000)
    raise ArgumentTypeError(f"{length_name} {run_duration.text} is not a whole number of steps of {step_size}. Use {' or '.join(nearest)}.")
