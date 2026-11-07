from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from ecosim_server import main as server_main
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources.config_files import config_file_path, config_file_path_str
from tests.data.generate_connection_config import (
    a_logical_delay,
    a_simulator,
    an_input,
    an_output,
    an_output_naming,
    config_file,
    error_of,
    load_config,
)


@pytest.mark.parametrize("index", ["0", 0], ids=["text", "number"])
def test_a_connection_to_an_output_of_another_simulator_is_accepted(tmp_path: Path, index: Any) -> None:
    house = a_simulator("house", an_input("T", simulator=index, interface="T_out"))

    config = load_config(tmp_path, a_simulator("weather", an_output("T_out")), house)

    assert config.clients[1].interfaces[0].connected_to[0].simulator_interface_id.simulator_name == "weather"


@pytest.mark.parametrize("index", ["-1", -1, "2", 2, "seven", None])
def test_an_index_outside_of_the_simulators_is_rejected_with_its_simulator_and_interface(tmp_path: Path, index: Any) -> None:
    message = error_of(tmp_path, a_simulator("weather", an_output("T_out")), a_simulator("house", an_input("T", simulator=index, interface="T_out")))

    assert f"simulator index '{index}'" in message
    assert "simulator 'house', interface 'T'" in message


def test_a_connection_to_an_input_is_rejected(tmp_path: Path) -> None:
    message = error_of(
        tmp_path,
        a_simulator("weather", an_output("T_out"), an_input("wind", simulator="1", interface="T_room")),
        a_simulator("house", an_input("T_out", simulator="0", interface="wind"), an_output("T_room")),
    )

    assert "simulator 'house', interface 'T_out': interface 'wind' of simulator 'weather' is an input" in message


def test_an_output_may_name_the_input_it_feeds(tmp_path: Path) -> None:
    weather = a_simulator("weather", an_output_naming("T_out", simulator="1", interface="T"))

    config = load_config(tmp_path, weather, a_simulator("house", an_input("T", simulator="0", interface="T_out")))

    assert config.clients[0].interfaces[0].connected_to[0].simulator_interface_id.simulator_name == "house"


def test_the_index_of_an_output_is_checked_too(tmp_path: Path) -> None:
    message = error_of(tmp_path, a_simulator("weather", an_output_naming("T_out", simulator="-1", interface="T_out")))

    assert "simulator 'weather', interface 'T_out': simulator index '-1'" in message


def test_a_connection_to_a_missing_interface_is_rejected(tmp_path: Path) -> None:
    message = error_of(tmp_path, a_simulator("weather", an_output("T_out")), a_simulator("house", an_input("T", simulator="0", interface="missing")))

    assert "simulator 'house', interface 'T': simulator 'weather' has no interface 'missing'" in message


@pytest.mark.parametrize("delay_path", [[], ["1"]])
def test_an_interface_connected_to_itself_is_rejected(tmp_path: Path, delay_path: list[str]) -> None:
    message = error_of(tmp_path, a_simulator("house", an_input("T", simulator="0", interface="T", delay_path=delay_path)))

    assert "simulator 'house', interface 'T': it is connected to itself" in message


def test_an_output_connected_to_itself_is_rejected(tmp_path: Path) -> None:
    message = error_of(tmp_path, a_simulator("house", an_output_naming("T", simulator="0", interface="T")))

    assert "simulator 'house', interface 'T': it is connected to itself" in message


def test_an_output_of_the_own_simulator_without_a_delay_is_rejected(tmp_path: Path) -> None:
    message = error_of(tmp_path, a_simulator("house", an_input("T", simulator="0", interface="T_room"), an_output("T_room")))

    assert "simulator 'house', interface 'T': output 'T_room' of its own simulator needs a logical delay" in message


def test_a_feedback_loop_through_a_logical_delay_stays_possible(tmp_path: Path) -> None:
    house = a_simulator("house", an_input("T", simulator="0", interface="T_room", delay_path=["1"]), an_output("T_room"))

    config = load_config(tmp_path, house, logical_delays=[a_logical_delay("house", "T")])

    assert config.logical_delays[0].logical_delay_connections[0].input_interface.model_interface_id.interface == "T_room"


def test_all_problems_are_reported_together(tmp_path: Path) -> None:
    targets = {"negative": ("-1", "T_out"), "too_high": ("9", "T_out"), "to_an_input": ("0", "negative"), "to_itself": ("0", "to_itself")}
    house = a_simulator("house", *[an_input(name, simulator=index, interface=target) for name, (index, target) in targets.items()])
    weather = a_simulator("weather", an_output("T_out"), an_input("missing", simulator="0", interface="unknown"))

    message = error_of(tmp_path, house, weather)

    for name in targets:
        assert f"simulator 'house', interface '{name}'" in message
    assert "simulator 'weather', interface 'missing'" in message


@pytest.mark.parametrize("file_name", ["simulation.json", "simulation_bergwald.json", "simulation_without_start_date.json"])
def test_the_test_configs_are_accepted(file_name: str) -> None:
    assert SimulationConfig.of_config_file_and_params(simulation_config_file=config_file_path(file_name), steps=1).clients


def test_the_server_does_not_start_with_an_invalid_connection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    file = config_file(tmp_path, a_simulator("weather", an_output("T_out")), a_simulator("house", an_input("T", simulator="-1", interface="T_out")))
    arguments = ["--server-config", config_file_path_str("server_config.ini"), "--simulation-config", str(file), "--steps", "1"]
    monkeypatch.setattr(sys, "argv", ["ecosim-server", *arguments])
    for name in ("sleep", "ShutdownManager", "init_logger", "create_repositories"):
        monkeypatch.setattr(server_main, name, MagicMock())
    server = MagicMock()
    monkeypatch.setattr(server_main, "Server", server)

    with pytest.raises(RuntimeError, match="simulator index '-1'"):
        server_main.main()

    server.assert_not_called()
