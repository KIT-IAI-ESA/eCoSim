from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from ecosim_server.config.simulation_config import SimulationConfig


def an_output(name: str) -> dict[str, Any]:
    return {"name": name, "type": "Output"}


def an_input(name: str, simulator: Any, interface: str, **fields: Any) -> dict[str, Any]:
    return {"name": name, "type": "Input", "connected_to": [{"simulator": simulator, "interface": interface, **fields}]}


def an_output_naming(name: str, simulator: Any, interface: str, **fields: Any) -> dict[str, Any]:
    return {**an_input(name, simulator=simulator, interface=interface, **fields), "type": "Output"}


def a_simulator(name: str, *interfaces: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "model": name, "interfaces": list(interfaces)}


def a_logical_delay(simulator: str, interface: str) -> dict[str, Any]:
    connection = {"destination_simulator_name": simulator, "destination_interface_name": interface, "start_value": "20.0"}
    return {"delay": "1", "output_connections": [connection]}


def config_file(tmp_path: Path, *simulators: dict[str, Any], logical_delays: list[dict[str, Any]] | None = None) -> Path:
    file = tmp_path / "simulation.json"
    file.write_text(json.dumps({"simulators": simulators, "logical_delays": logical_delays or [], "setup": {"delta_t": 1000}}))
    return file


def load_config(tmp_path: Path, *simulators: dict[str, Any], logical_delays: list[dict[str, Any]] | None = None) -> SimulationConfig:
    file = config_file(tmp_path, *simulators, logical_delays=logical_delays)
    return SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=1)


def error_of(tmp_path: Path, *simulators: dict[str, Any], logical_delays: list[dict[str, Any]] | None = None) -> str:
    with pytest.raises(RuntimeError) as error:
        load_config(tmp_path, *simulators, logical_delays=logical_delays)
    return str(error.value)
