from __future__ import annotations

from pathlib import Path

import pytest
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_server.results import read_results
from ecosim_server.simulation.state.simulation_state import SimulationState
from tests.results.stored_run import StoredRun


@pytest.fixture
def stored_run(tmp_path: Path) -> StoredRun:
    return StoredRun.in_directory(tmp_path)


def test_every_output_gets_a_column_named_after_its_simulator(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=2)

    table = read_results(tmp_path)

    assert table.column_names() == ("weather.T_out", "weather.profile[0]", "weather.profile[1]", "weather.profile[2]", "house.T_room")
    assert table.values("house.T_room") == [290.0, 290.0 + 1 / 3]


def test_an_array_gets_one_column_per_position(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=2)

    table = read_results(tmp_path).select(names=["weather.profile"])

    assert [list(row) for row in table.rows] == [[1.0, 2.0, 3.0], [1.0, 2.0, 4.0]]


def test_the_inputs_are_left_out_unless_they_are_asked_for(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=2)

    assert "house.T_out_in" not in read_results(tmp_path).column_names()
    assert read_results(directory=tmp_path, include_inputs=True).values("house.T_out_in") == [270.0, 271.0]


def test_with_the_inputs_each_simulator_shows_its_outputs_before_its_inputs(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=1)

    table = read_results(directory=tmp_path, include_inputs=True)

    # simulation.json lists the input of the house before its output
    assert table.column_names()[-2:] == ("house.T_room", "house.T_out_in")


def test_whole_numbers_and_booleans_become_floats(tmp_path: Path) -> None:
    values = (ProtocolInterfaceValue(name="count", value=3), ProtocolInterfaceValue(name="on", value=True))
    StoredRun.file_repository(directory=tmp_path, simulator_name="meter").add(values=values, timestamp=StoredRun.time_of(step=0))

    row = read_results(tmp_path).rows[0]

    assert row == (3.0, 1.0)
    assert [type(value) for value in row] == [float, float]


def test_a_null_value_of_an_array_gives_empty_cells_and_no_column_of_its_own(tmp_path: Path) -> None:
    repository = StoredRun.file_repository(directory=tmp_path, simulator_name="source")
    repository.add(values=(ProtocolInterfaceValue(name="y", value=[1.0, 2.0]),), timestamp=StoredRun.time_of(step=0))
    repository.add(values=(ProtocolInterfaceValue(name="y", value=None),), timestamp=StoredRun.time_of(step=1))

    table = read_results(tmp_path)

    assert table.column_names() == ("source.y[0]", "source.y[1]")
    assert table.rows == ((1.0, 2.0), (None, None))


def test_a_simulator_without_a_row_at_a_time_gets_empty_cells_there(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=3)
    StoredRun.file_repository(directory=tmp_path, simulator_name="house").remove_starting_at(timestamp=StoredRun.time_of(2))

    table = read_results(tmp_path)

    assert table.times == tuple(StoredRun.time_of(step) for step in range(3))
    assert table.values("house.T_room") == [290.0, 290.0 + 1 / 3, None]


def test_a_folder_with_two_runs_gives_the_last_run_and_says_so(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=5)
    stored_run.write_files(directory=tmp_path, steps=2)

    table = read_results(tmp_path)

    assert table.times == tuple(StoredRun.time_of(step) for step in range(2))
    assert "holds 2 runs" in table.warnings[0]


def test_the_simulation_config_can_be_given_for_a_folder_without_a_copy(tmp_path: Path, stored_run: StoredRun) -> None:
    results = tmp_path / "results"
    stored_run.write_files(directory=results, steps=1)

    table = read_results(directory=results, simulation_config=stored_run.simulation_config_file)

    assert "house.T_out_in" not in table.column_names()
    assert table.warnings == ()


def test_the_state_of_the_run_comes_with_the_table(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=1, state=SimulationState.FAILED)

    assert read_results(tmp_path).state is SimulationState.FAILED


def test_a_folder_without_states_gives_no_state(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=1)
    (tmp_path / "simulation_state.jsonl").unlink()

    assert read_results(tmp_path).state is None
