from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from tests.data.generate_connection_config import a_logical_delay, a_simulator, an_input, an_output, an_output_naming, error_of, load_config

WEATHER = a_simulator("weather", an_output("T_out"), an_output("wind"))
DELAY_OF_T = a_logical_delay("house", "T")
INPUT_SPELLINGS = ["input", "INPUT", "Input"]


@pytest.mark.parametrize(("entry", "delays"), [("1", []), ("2", [DELAY_OF_T]), (1, [DELAY_OF_T])])
def test_a_delay_path_naming_no_logical_delay_is_rejected(tmp_path: Path, entry: Any, delays: list[dict[str, Any]]) -> None:
    house = a_simulator("house", an_input("T", simulator="0", interface="T_out", delay_path=[entry]))

    message = error_of(tmp_path, WEATHER, house, logical_delays=delays)

    assert f"simulator 'house', interface 'T': delay_path entry {entry!r} names no logical delay" in message


def test_a_feedback_loop_whose_delay_path_names_no_logical_delay_is_rejected(tmp_path: Path) -> None:
    message = error_of(tmp_path, a_simulator("house", an_input("T", simulator="0", interface="T_room", delay_path=["1"]), an_output("T_room")))

    assert "simulator 'house', interface 'T': delay_path entry '1' names no logical delay" in message


def test_a_logical_delay_not_listing_the_input_is_rejected(tmp_path: Path) -> None:
    house = a_simulator(
        "house",
        an_input("T", simulator="0", interface="T_out", delay_path=["1"]),
        an_input("U", simulator="0", interface="wind", delay_path=["1"]),
    )

    message = error_of(tmp_path, WEATHER, house, logical_delays=[a_logical_delay("house", "U")])

    assert "simulator 'house', interface 'T': no logical delay in its delay_path lists it" in message
    assert "interface 'U'" not in message


def test_one_listing_logical_delay_in_the_path_is_enough(tmp_path: Path) -> None:
    house = a_simulator(
        "house",
        an_input("T", simulator="0", interface="T_out", delay_path=["1", "2"]),
        an_input("U", simulator="0", interface="wind", delay_path=["2"]),
    )

    assert load_config(tmp_path, WEATHER, house, logical_delays=[DELAY_OF_T, a_logical_delay("house", "U")]).logical_delays


@pytest.mark.parametrize("delay_path", [None, "1", 1, {"id": "1"}])
def test_a_delay_path_that_is_not_a_list_is_rejected(tmp_path: Path, delay_path: Any) -> None:
    house = a_simulator("house", an_input("T", simulator="0", interface="T_out", delay_path=delay_path))

    message = error_of(tmp_path, WEATHER, house)

    assert f"simulator 'house', interface 'T': delay_path must be a list, not {type(delay_path).__name__}" in message


def test_the_delay_path_of_an_output_must_be_a_list_too(tmp_path: Path) -> None:
    house = a_simulator(
        "house",
        an_input("T", simulator="0", interface="T_out"),
        an_output_naming("U", simulator="1", interface="T", delay_path=None),
    )

    assert "simulator 'house', interface 'U': delay_path must be a list, not NoneType" in error_of(tmp_path, WEATHER, house)


def test_the_delay_path_of_an_output_is_not_matched_against_the_logical_delays(tmp_path: Path) -> None:
    house = a_simulator(
        "house",
        an_input("T", simulator="0", interface="T_out"),
        an_output_naming("U", simulator="1", interface="T", delay_path=["9"]),
    )

    assert load_config(tmp_path, WEATHER, house).clients


def test_an_output_feeding_the_input_of_the_same_name_through_a_delay_is_accepted(tmp_path: Path) -> None:
    house = a_simulator("house", an_input("T", simulator="0", interface="T", delay_path=["1"]), an_output("T"))

    config = load_config(tmp_path, house, logical_delays=[DELAY_OF_T])

    assert config.logical_delays[0].logical_delay_connections[0].input_interface.model_interface_id.interface == "T"


def test_an_output_naming_the_input_of_the_same_name_is_accepted(tmp_path: Path) -> None:
    house = a_simulator("house", an_output_naming("T", simulator="0", interface="T"), {"name": "T", "type": "Input"})

    assert load_config(tmp_path, house).clients


def test_an_input_naming_the_output_of_the_same_name_still_needs_a_delay(tmp_path: Path) -> None:
    message = error_of(tmp_path, a_simulator("house", an_input("T", simulator="0", interface="T"), an_output("T")))

    assert "simulator 'house', interface 'T': output 'T' of its own simulator needs a logical delay" in message


@pytest.mark.parametrize(
    ("connected_to", "expected"),
    [
        ({"simulator": "0", "interface": "T_out"}, "connected_to must be a list, not dict"),
        ("0", "connected_to must be a list, not str"),
        (["0"], "a connection must be an object, not str"),
        ([{"simulator": "0", "interface": "T_out"}, {"simulator": "0", "interface": "wind"}], "connected_to has 2 connections, only one is possible"),
    ],
)
def test_a_wrong_connected_to_is_reported_with_the_other_problems(tmp_path: Path, connected_to: Any, expected: str) -> None:
    house = a_simulator("house", {"name": "T", "type": "Input", "connected_to": connected_to}, an_input("bad", simulator="-1", interface="T_out"))

    message = error_of(tmp_path, WEATHER, house)

    assert f"simulator 'house', interface 'T': {expected}" in message
    assert "simulator 'house', interface 'bad': simulator index '-1'" in message


@pytest.mark.parametrize("interface_type", INPUT_SPELLINGS)
def test_the_type_of_a_target_is_read_in_any_case(tmp_path: Path, interface_type: str) -> None:
    weather = a_simulator("weather", {"name": "wind", "type": interface_type})

    assert "is an input" in error_of(tmp_path, weather, a_simulator("house", an_input("T", simulator="0", interface="wind")))


@pytest.mark.parametrize("interface_type", INPUT_SPELLINGS)
def test_the_type_of_the_own_interface_is_read_in_any_case(tmp_path: Path, interface_type: str) -> None:
    own = {**an_input("T", simulator="0", interface="T_room"), "type": interface_type}

    assert "needs a logical delay" in error_of(tmp_path, a_simulator("house", own, an_output("T_room")))
