"""The keys of simulation.json that the server reads."""

from argparse import ArgumentTypeError
from pathlib import Path
from typing import Any

from ecosim_common.config.config_parser import ConfigParser


def missing_key_problems(raw_config: Any, simulation_config_file: Path, has_step_size_override: bool) -> list[str]:
    """Every key the server needs and does not find, and a delta_t it cannot use, one line each."""
    file = simulation_config_file
    if not isinstance(raw_config, dict):
        return [f'{file} has to hold a JSON object with the keys "setup", "simulators" and "logical_delays".']
    problems = [_missing_top_level_key(file=file, key=key) for key in ("setup", "simulators", "logical_delays") if key not in raw_config]
    if isinstance(raw_config.get("setup"), dict) and not has_step_size_override:
        problems += _delta_t_problems(file=file, setup=raw_config["setup"])
    simulators = raw_config.get("simulators")
    if isinstance(simulators, list):
        for index, simulator in enumerate(simulators):
            problems += _simulator_problems(file=file, simulator=simulator, index=index)
    return problems


def _missing_top_level_key(file: Path, key: str) -> str:
    # a simulation without delays still needs the empty list
    how_to_add = ' Write "logical_delays": [] if the simulation has none.' if key == "logical_delays" else ""
    return f'{file} has no key "{key}".{how_to_add}'


def _delta_t_problems(file: Path, setup: dict[str, Any]) -> list[str]:
    if "delta_t" not in setup:
        return [f'{file}: setup has no key "delta_t". Write the step size in milliseconds, like "delta_t": "900000", or pass --step-size.']
    delta_t = setup["delta_t"]
    # the loader reads a JSON number like 900000.0 as 900000
    if isinstance(delta_t, float) and delta_t.is_integer() and delta_t >= 1:
        return []
    try:
        ConfigParser.positive_whole_number(str(delta_t))
    except ArgumentTypeError as error:
        return [f"{file}: setup.delta_t {error}."]
    return []


def _simulator_problems(file: Path, simulator: Any, index: int) -> list[str]:
    if not isinstance(simulator, dict):
        return []
    where = f"simulator {simulator['name']}" if "name" in simulator else f"the simulator at index {index}"
    problems = [f'{file}: {where} has no key "{key}".' for key in ("name", "model", "interfaces") if key not in simulator]
    interfaces = simulator.get("interfaces")
    if isinstance(interfaces, list):
        problems += [
            f"{file}: {where}, {problem}"
            for interface_index, interface in enumerate(interfaces)
            for problem in _interface_problems(interface=interface, index=interface_index)
        ]
    return problems


def _interface_problems(interface: Any, index: int) -> list[str]:
    if not isinstance(interface, dict):
        return []
    where = f"interface {interface['name']}" if "name" in interface else f"the interface at index {index}"
    return [f'{where} has no key "{key}".' for key in ("name", "type") if key not in interface]
