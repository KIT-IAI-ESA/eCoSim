from ecosim.results.results_overview import overview_lines
from ecosim_server.simulation.state.simulation_state import SimulationState

from tests.results.stored_results import create_house_table_with, create_result_table


def test_the_overview_names_the_state_the_steps_and_the_simulated_period() -> None:
    lines = overview_lines(table=create_result_table(steps=4).without_inputs(), source="results", left_out_inputs=1)

    assert lines[:3] == [
        "Results:     results",
        "Run:         finished, 4 steps of 15 min",
        "Simulated:   2023-01-01 00:00 to 2023-01-01 01:00 UTC",
    ]


def test_a_long_run_counts_its_steps_with_thousands_commas() -> None:
    lines = overview_lines(table=create_result_table(steps=1200), source="results", left_out_inputs=0)

    assert lines[1] == "Run:         finished, 1,200 steps of 15 min"


def test_the_overview_says_how_many_inputs_are_left_out_and_how_to_show_them() -> None:
    lines = overview_lines(table=create_result_table().without_inputs(), source="results", left_out_inputs=1)

    assert lines[4] == "Columns:     1 output, 1 input is left out (add --inputs)"


def test_a_run_that_did_not_end_is_shown_as_not_finished() -> None:
    lines = overview_lines(table=create_result_table(state=SimulationState.READY), source="results", left_out_inputs=0)

    assert lines[1] == "Run:         not finished, 4 steps of 15 min. It is still running, or it was stopped."


def test_a_run_without_a_stored_step_has_simulated_nothing() -> None:
    lines = overview_lines(table=create_result_table(steps=0, state=SimulationState.FAILED), source="results", left_out_inputs=0)

    assert lines[1:3] == ["Run:         failed, 0 steps", "Simulated:   nothing"]


def test_every_column_gets_its_unit_and_its_minimum_mean_and_maximum() -> None:
    # uneven values, so that the mean differs from the median and from the middle of minimum and maximum
    table = create_house_table_with(rows=((290.0, 270.0), (290.0, 270.0), (296.0, 264.0)))

    lines = overview_lines(table=table, source="results", left_out_inputs=0)

    assert [line.split() for line in lines[-3:]] == [
        ["Column", "Unit", "Minimum", "Mean", "Maximum"],
        ["house.T_room", "K", "290", "292", "296"],
        ["house.T_out", "K", "264", "268", "270"],
    ]


def test_the_numbers_leave_out_the_empty_cells_of_a_simulator_that_stored_fewer_steps() -> None:
    table = create_house_table_with(rows=((290.0, 270.0), (None, 270.0), (296.0, 270.0)), state=SimulationState.FAILED)

    lines = overview_lines(table=table, source="results", left_out_inputs=0)

    assert lines[-2].split() == ["house.T_room", "K", "290", "293", "296"]


def test_a_column_without_a_value_shows_a_dash_for_each_number() -> None:
    table = create_house_table_with(rows=((290.0, None), (291.0, None)), state=SimulationState.FAILED)

    lines = overview_lines(table=table, source="results", left_out_inputs=0)

    assert lines[-1].split() == ["house.T_out", "K", "-", "-", "-"]
