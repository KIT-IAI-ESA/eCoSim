import json
import shutil
from pathlib import Path
from typing import Any, Callable

from ecosim.check.check_command import build_parser
from ecosim.check.simulation_check import SimulationCheck
from ecosim.simulation_command_line import SimulationCommandLine
from ecosim_test_common.resources.resource_utils import resource_path_file


def check_of(simulation: Path, *options: str) -> SimulationCheck:
    command_line = SimulationCommandLine.of_arguments(parser=build_parser(), passed_arguments=[str(simulation), *options], command_name="check")
    return SimulationCheck.of_simulation(simulation=command_line.simulation, run_options=command_line.run_options)


def change_json_file(file: Path, change: Callable[[Any], None]) -> None:
    content = json.loads(file.read_text(encoding="utf-8"))
    change(content)
    file.write_text(json.dumps(content, indent=4), encoding="utf-8")


def replace_in_file(file: Path, old: str, new: str) -> None:
    text = file.read_text(encoding="utf-8")
    if old not in text:
        raise ValueError(f"{file} has no {old!r}")
    file.write_text(text.replace(old, new), encoding="utf-8")


def interface_named(simulator: dict[str, Any], name: str) -> dict[str, Any]:
    return next(interface for interface in simulator["interfaces"] if interface["name"] == name)


def add_room_simulator(simulation: Path) -> Path:
    room = simulation / "modules" / "room"
    shutil.copytree(src=resource_path_file("python/room"), dst=room, ignore=shutil.ignore_patterns("__pycache__"))
    weather_index = "2"
    interfaces = [
        {"name": "heating_power", "type": "Input", "connected_to": [{"simulator": weather_index, "interface": "weatherBus.TDryBul"}]},
        {"name": "temperature", "type": "Output"},
    ]
    change_json_file(
        file=simulation / "server" / "simulation.json",
        change=lambda config: config["simulators"].append({"name": "room", "model": "room", "interfaces": interfaces}),
    )
    return room
