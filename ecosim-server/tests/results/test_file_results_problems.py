from __future__ import annotations

from pathlib import Path

import pytest
from ecosim_common.tech.one_line_errors import one_line_message
from ecosim_server.results import read_results
from tests.results.stored_run import StoredRun


@pytest.fixture
def stored_run(tmp_path: Path) -> StoredRun:
    return StoredRun.in_directory(tmp_path)


def test_without_simulation_json_the_inputs_cannot_be_left_out(tmp_path: Path, stored_run: StoredRun) -> None:
    results = tmp_path / "results"
    stored_run.write_files(directory=results, steps=1)

    table = read_results(results)

    assert "house.T_out_in" in table.column_names()
    assert "no simulation.json" in table.warnings[0]


def test_a_listed_simulator_without_results_is_named_in_a_warning(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=1)
    StoredRun.file_repository(directory=tmp_path, simulator_name="house").file_path().unlink()

    table = read_results(tmp_path)

    assert table.warnings == (f"{tmp_path} has no results of house, which {stored_run.simulation_config_file} lists.",)


def test_the_results_of_a_simulator_that_the_simulation_config_does_not_list_are_left_out_with_a_warning(
    tmp_path: Path,
    stored_run: StoredRun,
) -> None:
    stored_run.write_files(directory=tmp_path, steps=1)
    old_values = stored_run.values_of(simulator_name=stored_run.weather, step=0)
    StoredRun.file_repository(directory=tmp_path, simulator_name="old").add(values=old_values, timestamp=StoredRun.time_of(step=0))

    table = read_results(tmp_path)

    assert "old.T_out" not in table.column_names()
    assert table.warnings == (f"{stored_run.simulation_config_file} does not list old, so the table leaves out module_old.jsonl.",)


def test_a_simulation_config_that_lists_none_of_the_stored_simulators_is_refused(tmp_path: Path, stored_run: StoredRun) -> None:
    results = tmp_path / "results"
    stored_run.write_files(directory=results, steps=1)
    other_config_file = StoredRun.in_directory(directory=results, weather="weather_x", house="house_x").simulation_config_file

    with pytest.raises(ValueError) as raised:
        read_results(results)

    assert str(raised.value) == f"{results} holds no results of the simulators that {other_config_file} lists: weather_x, house_x."


def test_a_simulation_config_without_simulators_is_named_in_the_error(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=1)
    fmc_file = tmp_path / "house.fmc"
    fmc_file.write_text('{"inputs": [], "outputs": []}')

    with pytest.raises(ValueError) as raised:
        read_results(directory=tmp_path, simulation_config=fmc_file)

    assert one_line_message(error=raised.value) == f'{fmc_file} has no key "simulators".'


def test_a_given_simulation_config_that_does_not_exist_is_named_in_the_error(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=1)
    missing = tmp_path / "simulaton.json"

    with pytest.raises(FileNotFoundError) as raised:
        read_results(directory=tmp_path, simulation_config=missing)

    assert one_line_message(error=raised.value) == f"No such file or directory: {missing}"


def test_a_missing_folder_is_named_in_the_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="results does not exist"):
        read_results(tmp_path / "results")


def test_reading_leaves_a_missing_folder_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_results(tmp_path / "results")

    assert not (tmp_path / "results").exists()


def test_a_file_given_as_the_folder_names_the_folder_that_holds_it(tmp_path: Path, stored_run: StoredRun) -> None:
    stored_run.write_files(directory=tmp_path, steps=1)
    house_file = StoredRun.file_repository(directory=tmp_path, simulator_name="house").file_path()

    with pytest.raises(NotADirectoryError) as raised:
        read_results(house_file)

    assert str(raised.value) == f"{house_file} is a file. Give the folder that holds it: {tmp_path}."


def test_a_folder_without_result_files_is_named_in_the_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError) as raised:
        read_results(tmp_path)

    assert str(raised.value) == f"{tmp_path} holds no results: there is no module_<simulator>.jsonl in it."
