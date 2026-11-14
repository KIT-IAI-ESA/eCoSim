from argparse import ArgumentTypeError
from datetime import datetime
from pathlib import Path
from typing import Any

from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.close_name import closest_name, did_you_mean
from ecosim_common.tech.json.unknown_json_keys import unknown_key_warnings_of_entries, unknown_key_warnings_of_object

DEFAULT_START_DATE = "2024-01-01T00:00:00.000Z"
TOP_LEVEL_KEYS = ("setup", "simulators", "logical_delays")
SETUP_KEYS = ("delta_t", "steps", "start_date")
# the keys the loader reads, by the kind of entry that has them
READ_KEYS = {
    "simulator": ("name", "model", "interfaces"),
    "interface": ("name", "type", "unit", "description", "required", "connected_to"),
    "connection": ("simulator", "interface", "delay_path"),
    "logical delay": ("delay", "output_connections"),
    "output connection": ("destination_simulator_name", "destination_interface_name", "start_value"),
}


def missing_key_problems(
    raw_config: dict[str, Any],
    simulation_config_file: Path,
    has_step_size_override: bool,
    has_steps_override: bool,
) -> list[str]:
    """Every key the server needs and does not find, and a delta_t or steps it cannot use, one line each."""
    file = simulation_config_file
    problems = [_missing_top_level_key(file=file, key=key) for key in TOP_LEVEL_KEYS if key not in raw_config]
    if isinstance(raw_config.get("setup"), dict):
        problems += _setup_problems(
            file=file,
            setup=raw_config["setup"],
            has_step_size_override=has_step_size_override,
            has_steps_override=has_steps_override,
        )
    return problems + _problems_of_simulators(file=file, simulators=raw_config.get("simulators"))


def simulator_key_problems(raw_config: Any, simulation_config_file: Path) -> list[str]:
    file = simulation_config_file
    if not isinstance(raw_config, dict) or "simulators" not in raw_config:
        return [_missing_top_level_key(file=file, key="simulators")]
    return _problems_of_simulators(file=file, simulators=raw_config["simulators"])


def unknown_key_warnings(raw_config: dict[str, Any], simulation_config_file: Path) -> list[str]:
    """One warning for each key that nothing reads, counted per kind of entry, for a config without missing keys."""
    file = simulation_config_file
    entries_by_noun = _entries_by_noun(raw_config=raw_config)
    setup = raw_config["setup"] if isinstance(raw_config["setup"], dict) else {}
    return [
        *unknown_key_warnings_of_object(where=str(file), raw_object=raw_config, read_keys=TOP_LEVEL_KEYS),
        *[_setup_warning(file=file, key=key, setup=setup) for key in setup if key not in SETUP_KEYS],
        *[
            warning
            for noun, read_keys in READ_KEYS.items()
            for warning in unknown_key_warnings_of_entries(where=str(file), noun=noun, entries=entries_by_noun[noun], read_keys=read_keys)
        ],
    ]


def _setup_warning(file: Path, key: str, setup: dict[str, Any]) -> str:
    # a run without start_date still starts, but at a date the simulation may not expect
    starts_at_the_default = closest_name(name=key, known_names=SETUP_KEYS) == "start_date" and "start_date" not in setup
    default = f" Without it the run starts at {datetime.fromisoformat(DEFAULT_START_DATE):%Y-%m-%d %H:%M} UTC." if starts_at_the_default else ""
    return f'{file}: setup has the key "{key}", which nothing reads.{did_you_mean(name=key, known_names=SETUP_KEYS)}{default}'


def _entries_by_noun(raw_config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    simulators = _entries_of(value=raw_config["simulators"])
    interfaces = [interface for simulator in simulators for interface in _entries_of(value=simulator.get("interfaces"))]
    delays = _entries_of(value=raw_config["logical_delays"])
    return {
        "simulator": simulators,
        "interface": interfaces,
        "connection": [connection for interface in interfaces for connection in _entries_of(value=interface.get("connected_to"))],
        "logical delay": delays,
        "output connection": [connection for delay in delays for connection in _entries_of(value=delay.get("output_connections"))],
    }


def _entries_of(value: Any) -> list[dict[str, Any]]:
    # an entry of another type is a problem that the loader names
    return [entry for entry in value if isinstance(entry, dict)] if isinstance(value, list) else []


def _problems_of_simulators(file: Path, simulators: Any) -> list[str]:
    if not isinstance(simulators, list):
        return []
    return [problem for index, simulator in enumerate(simulators) for problem in _simulator_problems(file=file, simulator=simulator, index=index)]


def _missing_top_level_key(file: Path, key: str) -> str:
    how_to_add = ' Write "logical_delays": [] if the simulation has none.' if key == "logical_delays" else ""
    return f'{file} has no key "{key}".{how_to_add}'


def _setup_problems(file: Path, setup: dict[str, Any], has_step_size_override: bool, has_steps_override: bool) -> list[str]:
    problems: list[str] = []
    if not has_step_size_override:
        how_to_add = 'Write the step size in milliseconds, like "delta_t": "900000", or pass --step-size.'
        problems += _whole_number_problems(file=file, setup=setup, key="delta_t", how_to_add=how_to_add)
    if not has_steps_override:
        how_to_add = 'Write how many steps the simulation runs, like "steps": 96, or pass --steps.'
        problems += _whole_number_problems(file=file, setup=setup, key="steps", how_to_add=how_to_add)
    return problems


def _whole_number_problems(file: Path, setup: dict[str, Any], key: str, how_to_add: str) -> list[str]:
    if key not in setup:
        return [f'{file}: setup has no key "{key}". {how_to_add}']
    value = setup[key]
    # the loader reads a JSON number like 900000.0 as 900000
    if isinstance(value, float) and value.is_integer() and value >= 1:
        return []
    try:
        ConfigParser.positive_whole_number(str(value))
    except ArgumentTypeError as error:
        return [f"{file}: setup.{key} {error}."]
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
