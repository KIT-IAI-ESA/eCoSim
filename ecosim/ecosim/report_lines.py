import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Mapping, Sequence, assert_never

from ecosim_common.client.config.client_type import ClientType
from ecosim_common.tech.datetime.readable_duration import readable_duration
from ecosim_common.tech.readable_count import readable_count
from ecosim_server.config.simulation_config import SimulationConfig

from ecosim.check.checked_simulator import CheckedSimulator


def simulator_lines(simulators: Sequence[CheckedSimulator]) -> list[str]:
    rows = [
        (
            simulator.name,
            client_type_text(client_type=simulator.client_type),
            shown_path(path=simulator.directory.path),
            readable_count(count=simulator.input_count, noun="input"),
            readable_count(count=simulator.output_count, noun="output"),
        )
        for simulator in simulators
    ]
    widths = [max(len(row[column]) for row in rows) for column in range(5)] if rows else []
    return [
        f"  {name:<{widths[0]}}  {kind:<{widths[1]}}  {directory:<{widths[2]}}  {inputs:>{widths[3]}}  {outputs:>{widths[4]}}"
        for name, kind, directory, inputs, outputs in rows
    ]


def length_line(simulation_config: SimulationConfig) -> str:
    steps = readable_count(count=simulation_config.steps, noun="step")
    step_size = readable_duration(seconds=simulation_config.step_size_in_ms / 1000)
    return f"{steps} of {step_size}, from {simulation_config.simulated_period_text(completed_steps=simulation_config.steps)}."


def client_type_text(client_type: ClientType) -> str:
    match client_type:
        case ClientType.FMU_2:
            return "FMI 2.0"
        case ClientType.FMU_3:
            return "FMI 3.0"
        case ClientType.Matlab:
            return "MATLAB"
        case ClientType.Pyro5:
            return "Pyro5"
        case ClientType.Python:
            return "Python"
        case _:
            assert_never(client_type)


def shown_path(path: Path) -> str:
    """Returns the path relative to the current folder when it is inside it."""
    absolute = path.absolute()
    return os.path.relpath(absolute) if absolute.is_relative_to(Path.cwd()) else str(absolute)


def ecosim_program(environment: Mapping[str, str] = os.environ) -> list[str]:
    # uv run sets UV
    return ["uv", "run", "ecosim"] if environment.get("UV") else ["ecosim"]


def command_text(arguments: Sequence[str]) -> str:
    # the shells of Windows know no single quotes
    return subprocess.list2cmdline(arguments) if sys.platform == "win32" else shlex.join(arguments)


def with_shown_paths(text: str) -> str:
    """Replaces absolute paths inside the current folder with relative ones."""
    return text.replace(f"{Path.cwd()}{os.sep}", "")


def and_joined(texts: Sequence[str]) -> str:
    return texts[0] if len(texts) == 1 else f"{', '.join(texts[:-1])} and {texts[-1]}"


def it_or_them(count: int) -> str:
    return "it" if count == 1 else "them"
