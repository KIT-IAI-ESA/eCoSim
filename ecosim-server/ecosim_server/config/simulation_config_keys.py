from argparse import ArgumentTypeError
from pathlib import Path
from typing import Any

from ecosim_common.config.config_parser import ConfigParser


def missing_key_problems(raw_config: dict[str, Any], simulation_config_file: Path, has_step_size_override: bool) -> list[str]:
    file = simulation_config_file
    problems = [_missing_top_level_key(file=file, key=key) for key in ("setup", "simulators", "logical_delays") if key not in raw_config]
    if isinstance(raw_config.get("setup"), dict) and not has_step_size_override:
        problems += _delta_t_problems(file=file, setup=raw_config["setup"])
    return problems + _problems_of_simulators(file=file, simulators=raw_config.get("simulators"))


def simulator_key_problems(raw_config: Any, simulation_config_file: Path) -> list[str]:
    file = simulation_config_file
    if not isinstance(raw_config, dict) or "simulators" not in raw_config:
        return [_missing_top_level_key(file=file, key="simulators")]
    return _problems_of_simulators(file=file, simulators=raw_config["simulators"])


def _problems_of_simulators(file: Path, simulators: Any) -> list[str]:
    if not isinstance(simulators, list):
        return []
    return [problem for index, simulator in enumerate(simulators) for problem in _simulator_problems(file=file, simulator=simulator, index=index)]


def _missing_top_level_key(file: Path, key: str) -> str:
    how_to_add = ' Write "logical_delays": [] if the simulation has none.' if key == "logical_delays" else ""
    return f'{file} has no key "{key}".{how_to_add}'


def _delta_t_problems(file: Path, setup: dict[str, Any]) -> list[str]:
    if "delta_t" not in setup:
        return [f'{file}: setup has no key "delta_t". Set it to the step size in milliseconds or pass --step-size.']
    delta_t = setup["delta_t"]
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
