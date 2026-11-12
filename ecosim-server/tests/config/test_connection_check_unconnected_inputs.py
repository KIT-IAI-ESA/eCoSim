from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from ecosim_test_common.test_data.generate_simulation_file import a_logical_delay, a_simulator, an_input, an_output
from tests.data.generate_connection_config import error_of, load_config

WEATHER = a_simulator("weather", an_output("T_out"))
NO_CONNECTION = [pytest.param({}, id="missing"), pytest.param({"connected_to": None}, id="null"), pytest.param({"connected_to": []}, id="empty")]


@pytest.mark.parametrize("no_connection", NO_CONNECTION)
def test_an_input_without_a_connection_is_rejected(tmp_path: Path, no_connection: dict[str, Any]) -> None:
    house = a_simulator("house", {"name": "T", "type": "Input", **no_connection})

    message = error_of(tmp_path, WEATHER, house)

    assert "simulator 'house', interface 'T': the input has no connection in connected_to" in message


def test_an_unconnected_input_is_reported_with_the_other_problems(tmp_path: Path) -> None:
    house = a_simulator("house", {"name": "T", "type": "Input"}, an_input("bad", simulator="-1", interface="T_out"))

    message = error_of(tmp_path, WEATHER, house)

    assert "simulator 'house', interface 'T': the input has no connection in connected_to" in message
    assert "simulator 'house', interface 'bad': simulator index '-1'" in message


def test_an_input_with_a_misspelt_connected_to_is_rejected(tmp_path: Path) -> None:
    house = a_simulator("house", {"name": "T", "type": "Input", "connectedTo": [{"simulator": "0", "interface": "T_out"}]})

    message = error_of(tmp_path, WEATHER, house)

    assert "simulator 'house', interface 'T': the input has no connection in connected_to" in message


def test_a_logical_delay_alone_does_not_connect_an_input(tmp_path: Path) -> None:
    house = a_simulator("house", {"name": "T", "type": "Input"}, an_output("T_room"))

    message = error_of(tmp_path, house, logical_delays=[a_logical_delay(simulator="house", interface="T")])

    assert "simulator 'house', interface 'T': the input has no connection in connected_to" in message


@pytest.mark.parametrize("no_connection", NO_CONNECTION)
def test_an_output_without_a_connection_is_still_accepted(tmp_path: Path, no_connection: dict[str, Any]) -> None:
    weather = a_simulator("weather", {"name": "T_out", "type": "Output", **no_connection})

    config = load_config(tmp_path, weather, a_simulator("house", an_input("T", simulator="0", interface="T_out")))

    assert config.clients[0].interfaces[0].connected_to == []
