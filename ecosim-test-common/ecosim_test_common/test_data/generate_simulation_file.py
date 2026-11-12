from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def an_output(name: str) -> dict[str, Any]:
    return {"name": name, "type": "Output"}


def an_input(name: str, simulator: Any, interface: str, **fields: Any) -> dict[str, Any]:
    return {"name": name, "type": "Input", "connected_to": [{"simulator": simulator, "interface": interface, **fields}]}


def an_output_naming(name: str, simulator: Any, interface: str, **fields: Any) -> dict[str, Any]:
    return {**an_input(name, simulator=simulator, interface=interface, **fields), "type": "Output"}


def a_simulator(name: str, *interfaces: dict[str, Any], model: str | None = None) -> dict[str, Any]:
    return {"name": name, "model": model or name, "interfaces": list(interfaces)}


def a_logical_delay(simulator: str, interface: str, delay: int = 1, start_value: Any = "20.0") -> dict[str, Any]:
    connection = {"destination_simulator_name": simulator, "destination_interface_name": interface, "start_value": start_value}
    return {"delay": str(delay), "output_connections": [connection]}


def config_file(directory: Path, *simulators: dict[str, Any], logical_delays: list[dict[str, Any]] | None = None) -> Path:
    file = directory / "simulation.json"
    file.write_text(json.dumps({"simulators": simulators, "logical_delays": logical_delays or [], "setup": {"delta_t": 1000}}))
    return file
