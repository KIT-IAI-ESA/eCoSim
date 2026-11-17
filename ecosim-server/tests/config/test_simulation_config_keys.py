from pathlib import Path
from typing import Any

from ecosim_server.config.simulation_config_keys import missing_key_problems
from ecosim_test_common.test_data.generate_simulation_file import create_input, create_output, create_simulator

FILE = Path("server/simulation.json")


def _a_complete_config() -> dict[str, Any]:
    weather = create_simulator("weather", create_output("T_out"))
    house = create_simulator("house", create_input("T_out", simulator="0", interface="T_out"))
    return {"setup": {"delta_t": "900000"}, "simulators": [weather, house], "logical_delays": []}


def test_a_complete_config_has_no_problems() -> None:
    assert missing_key_problems(raw_config=_a_complete_config(), simulation_config_file=FILE, has_step_size_override=False) == []


def test_every_missing_key_is_listed_with_the_file() -> None:
    raw_config: dict[str, Any] = {"simulators": []}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False) == [
        f'{FILE} has no key "setup".',
        f'{FILE} has no key "logical_delays". Write "logical_delays": [] if the simulation has none.',
    ]


def test_a_delta_t_below_1_is_a_problem_with_its_value() -> None:
    raw_config = {**_a_complete_config(), "setup": {"delta_t": 0}}

    (problem,) = missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False)

    assert problem.startswith(f"{FILE}: setup.delta_t ")
    assert "'0'" in problem


def test_a_missing_delta_t_says_how_to_set_the_step_size() -> None:
    raw_config = {**_a_complete_config(), "setup": {}}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False) == [
        f'{FILE}: setup has no key "delta_t". Set it to the step size in milliseconds or pass --step-size.',
    ]


def test_a_delta_t_written_with_a_zero_fraction_is_a_whole_number() -> None:
    raw_config = {**_a_complete_config(), "setup": {"delta_t": 900000.0}}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False) == []


def test_json_that_is_not_an_object_is_a_problem_with_the_keys_it_needs() -> None:
    assert missing_key_problems(raw_config=[], simulation_config_file=FILE, has_step_size_override=False) == [
        f'{FILE} has to contain a JSON object with the keys "setup", "simulators" and "logical_delays".',
    ]


def test_a_simulator_and_an_interface_with_a_missing_key_are_listed() -> None:
    house = create_simulator("house", {"name": "T_out"})
    del house["model"]
    raw_config = {**_a_complete_config(), "simulators": [house]}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False) == [
        f'{FILE}: simulator house has no key "model".',
        f'{FILE}: simulator house, interface T_out has no key "type".',
    ]
