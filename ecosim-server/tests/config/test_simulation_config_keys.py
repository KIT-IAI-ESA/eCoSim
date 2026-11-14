import logging
from pathlib import Path
from typing import Any

import pytest
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_common.tech.json.read_json_file import read_json_file
from ecosim_server.config.simulation_config_keys import missing_key_problems, simulator_key_problems, unknown_key_warnings
from ecosim_test_common.resources.resource_utils import resource_path
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_input, create_logical_delay, create_output, create_simulator

FILE = Path("server/simulation.json")


def _a_complete_config() -> dict[str, Any]:
    weather = create_simulator("weather", create_output("T_out"))
    house = create_simulator("house", create_input("T_out", simulator="0", interface="T_out"))
    return {"setup": {"delta_t": "900000", "steps": 96}, "simulators": [weather, house], "logical_delays": []}


def test_a_complete_config_has_no_problems() -> None:
    assert (
        missing_key_problems(raw_config=_a_complete_config(), simulation_config_file=FILE, has_step_size_override=False, has_steps_override=False)
        == []
    )


def test_every_missing_key_is_listed_with_the_file() -> None:
    raw_config: dict[str, Any] = {"simulators": []}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False, has_steps_override=True) == [
        f'{FILE} has no key "setup".',
        f'{FILE} has no key "logical_delays". Write "logical_delays": [] if the simulation has none.',
    ]


def test_a_delta_t_below_1_is_a_problem_with_its_value() -> None:
    raw_config = {**_a_complete_config(), "setup": {"delta_t": "0"}}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False, has_steps_override=True) == [
        f"{FILE}: setup.delta_t must be a whole number of at least 1, not '0'.",
    ]


def test_a_missing_delta_t_says_how_to_set_the_step_size() -> None:
    raw_config = {**_a_complete_config(), "setup": {}}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False, has_steps_override=True) == [
        f'{FILE}: setup has no key "delta_t". Write the step size in milliseconds, like "delta_t": "900000", or pass --step-size.',
    ]


def test_a_delta_t_written_with_a_zero_fraction_is_a_whole_number() -> None:
    raw_config = {**_a_complete_config(), "setup": {"delta_t": 900000.0}}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False, has_steps_override=True) == []


def test_a_simulator_and_an_interface_with_a_missing_key_are_listed() -> None:
    house = create_simulator("house", {"name": "T_out"})
    del house["model"]
    raw_config = {**_a_complete_config(), "simulators": [house]}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False, has_steps_override=True) == [
        f'{FILE}: simulator house has no key "model".',
        f'{FILE}: simulator house, interface T_out has no key "type".',
    ]


def test_the_results_need_only_the_simulators_and_their_interfaces() -> None:
    assert simulator_key_problems(raw_config={"simulators": _a_complete_config()["simulators"]}, simulation_config_file=FILE) == []
    assert simulator_key_problems(raw_config={"setup": {}}, simulation_config_file=FILE) == [f'{FILE} has no key "simulators".']


def test_a_number_of_steps_below_1_is_named_with_its_value() -> None:
    raw_config = {**_a_complete_config(), "setup": {"delta_t": "900000", "steps": 0}}

    assert missing_key_problems(raw_config=raw_config, simulation_config_file=FILE, has_step_size_override=False, has_steps_override=False) == [
        f"{FILE}: setup.steps must be a whole number of at least 1, not '0'.",
    ]


def test_every_key_that_the_loader_reads_is_known() -> None:
    sender = create_simulator("sender", {**create_output("sent"), "unit": "K", "description": "", "required": "false"})
    receiver = create_simulator("receiver", create_input("delayed", simulator="0", interface="sent", delay_path=["1"]))
    raw_config = {
        "setup": {"delta_t": "900000", "steps": 96, "start_date": "2023-01-01T00:00:00.000Z"},
        "simulators": [sender, receiver],
        "logical_delays": [create_logical_delay("receiver", "delayed")],
    }

    assert unknown_key_warnings(raw_config=raw_config, simulation_config_file=FILE) == []


# so the tests that load them log no warning
@pytest.mark.parametrize("file", sorted(resource_path().rglob("simulation*.json")), ids=lambda file: str(file.relative_to(resource_path())))
def test_the_simulation_configs_of_the_test_resources_have_no_key_that_nothing_reads(file: Path) -> None:
    assert unknown_key_warnings(raw_config=read_json_file(file=file), simulation_config_file=file) == []


def test_a_misspelt_start_date_is_a_warning_that_names_the_default() -> None:
    raw_config = {**_a_complete_config(), "setup": {"delta_t": "900000", "start-date": "2023-01-01T00:00:00.000Z"}}

    assert unknown_key_warnings(raw_config=raw_config, simulation_config_file=FILE) == [
        f'{FILE}: setup has the key "start-date", which nothing reads. Did you mean start_date? Without it the run starts at 2024-01-01 00:00 UTC.',
    ]


def test_a_misspelt_start_date_next_to_start_date_does_not_name_the_default() -> None:
    raw_config = {
        **_a_complete_config(),
        "setup": {"delta_t": "900000", "start_date": "2023-01-01T00:00:00.000Z", "start-date": "2023-06-01T00:00:00.000Z"},
    }

    assert unknown_key_warnings(raw_config=raw_config, simulation_config_file=FILE) == [
        f'{FILE}: setup has the key "start-date", which nothing reads. Did you mean start_date?',
    ]


def test_a_key_that_nothing_reads_is_warned_once_with_the_number_of_entries_that_have_it() -> None:
    weather = create_simulator("weather", {**create_output("T_out"), "report": "true"}, {**create_output("wind"), "report": "true"})
    raw_config = {**_a_complete_config(), "simulators": [weather], "comment": "first try"}

    assert unknown_key_warnings(raw_config=raw_config, simulation_config_file=FILE) == [
        f'{FILE} has the key "comment", which nothing reads.',
        f'{FILE}: 2 interfaces have the key "report", which nothing reads.',
    ]


def test_the_loader_logs_each_key_that_nothing_reads(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    file = config_file(tmp_path, create_simulator("weather", {**create_output("T_out"), "report": "true"}))

    SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=1)

    assert [(record.levelno, record.getMessage()) for record in caplog.records if record.name == "SimulationConfig"] == [
        (logging.WARNING, f'{file}: 1 interface has the key "report", which nothing reads.'),
    ]


def test_a_misspelt_key_is_warned_also_when_the_config_then_fails_to_load(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    house = create_simulator("house", {"name": "T_out", "type": "Input", "connected-to": [{"simulator": "0", "interface": "T_out"}]})
    file = config_file(tmp_path, create_simulator("weather", create_output("T_out")), house)

    with pytest.raises(RuntimeError, match="the input has no connection in connected_to"):
        SimulationConfig.of_config_file_and_params(simulation_config_file=file, steps=1)

    assert [(record.levelno, record.getMessage()) for record in caplog.records if record.name == "SimulationConfig"] == [
        (logging.WARNING, f'{file}: 1 interface has the key "connected-to", which nothing reads. Did you mean connected_to?'),
    ]
