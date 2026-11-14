from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

import pandas
import pytest
from ecosim_server.results import ResultTable, read_results
from tests.results.stored_run import StoredRun


@pytest.fixture
def table(tmp_path: Path) -> ResultTable:
    StoredRun.in_directory(tmp_path).write_files(directory=tmp_path, steps=3)
    return read_results(tmp_path)


def test_select_keeps_the_named_columns_in_the_order_of_the_names(table: ResultTable) -> None:
    assert table.select(names=["house.T_room", "weather.T_out"]).column_names() == ("house.T_room", "weather.T_out")


def test_a_simulator_or_an_array_name_selects_all_its_columns(table: ResultTable) -> None:
    assert table.select(names=["weather.profile"]).column_names() == ("weather.profile[0]", "weather.profile[1]", "weather.profile[2]")
    assert table.select(names=["house"]).column_names() == ("house.T_room",)


def test_the_values_of_a_name_that_picks_several_columns_are_refused(table: ResultTable) -> None:
    with pytest.raises(ValueError) as raised:
        table.values("weather.profile")

    assert str(raised.value) == "weather.profile picks 3 columns. Give the name of one of them, like weather.profile[0]."


def test_a_misspelt_name_gets_the_closest_column_as_a_hint(table: ResultTable) -> None:
    with pytest.raises(ValueError) as raised:
        table.select(names=["house.T_rom"])

    assert str(raised.value) == "The results have no column house.T_rom. Did you mean house.T_room?"


def test_a_left_out_input_says_how_to_read_it(table: ResultTable) -> None:
    with pytest.raises(ValueError) as raised:
        table.values("house.T_out_in")

    assert str(raised.value) == "house.T_out_in is an input, which the table leaves out. Read it with include_inputs=True."


def test_matches_says_whether_a_name_picks_any_column(table: ResultTable) -> None:
    assert table.matches("house")
    assert table.matches("weather.profile")
    assert table.matches("house.t_room")
    assert not table.matches("house.T_rom")


def test_a_name_in_another_case_finds_the_lower_case_column(table: ResultTable) -> None:
    lower_case = replace(table, columns=tuple(replace(column, interface_name=column.interface_name.lower()) for column in table.columns))

    assert lower_case.select(names=["house.T_room"]).column_names() == ("house.t_room",)


def test_the_csv_has_a_time_column_and_keeps_every_digit(table: ResultTable, tmp_path: Path) -> None:
    csv_file = tmp_path / "results.csv"

    table.write_csv(csv_file)

    with csv_file.open(newline="") as file:
        header, *rows = list(csv.reader(file))
    assert header == ["time", *table.column_names()]
    assert [row[0] for row in rows] == [time.isoformat() for time in table.times]
    assert [[float(cell) for cell in row[1:]] for row in rows] == [list(row) for row in table.rows]


def test_the_data_frame_has_the_times_as_index_and_a_column_per_interface(table: ResultTable) -> None:
    frame = table.to_data_frame()

    assert list(frame.columns) == list(table.column_names())
    assert list(frame.index) == [pandas.Timestamp(time) for time in table.times]
    assert frame["house.T_room"].tolist() == table.values("house.T_room")
