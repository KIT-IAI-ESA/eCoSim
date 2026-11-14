from argparse import ArgumentTypeError

import pytest
from ecosim.run_length import Duration, duration, step_size_in_milliseconds, steps_of_duration


def test_a_duration_becomes_the_number_of_steps_of_the_step_size() -> None:
    assert steps_of_duration(run_duration=duration(text="365d"), step_size_in_milliseconds=900_000) == 35_040
    assert steps_of_duration(run_duration=duration(text="1y"), step_size_in_milliseconds=900_000) == 35_040


def test_a_duration_that_is_no_whole_number_of_steps_names_the_two_nearest_step_counts() -> None:
    with pytest.raises(ArgumentTypeError) as error:
        steps_of_duration(run_duration=duration(text="1h"), step_size_in_milliseconds=7 * 60_000)

    assert str(error.value) == "--duration 1h is not a whole number of steps of 7 min. Use --steps 8 (56 min) or --steps 9 (1 h 3 min)."


def test_a_duration_shorter_than_one_step_names_one_step() -> None:
    with pytest.raises(ArgumentTypeError) as error:
        steps_of_duration(run_duration=duration(text="5min"), step_size_in_milliseconds=900_000)

    assert str(error.value).endswith("Use --steps 1 (15 min).")


@pytest.mark.parametrize("text", ["15m", "3w", "fast", "min"])
def test_a_duration_without_a_known_unit_lists_the_units(text: str) -> None:
    with pytest.raises(ArgumentTypeError) as error:
        duration(text=text)

    assert str(error.value) == f"must be a number with one of the units ms, s, min, h, d or y, like 15min, not '{text}'"


@pytest.mark.parametrize("text, milliseconds", [("15min", 900_000), ("1.5h", 5_400_000), ("0.3s", 300), ("2 d", 172_800_000), ("90ms", 90)])
def test_a_duration_with_decimals_is_read_exactly(text: str, milliseconds: int) -> None:
    assert duration(text=text) == Duration(text=text, milliseconds=milliseconds)


@pytest.mark.parametrize("text", ["0s", "0.5ms", "1.5ms"])
def test_a_duration_below_one_millisecond_or_between_two_is_refused(text: str) -> None:
    with pytest.raises(ArgumentTypeError) as error:
        duration(text=text)

    assert str(error.value) == f"must be a whole number of milliseconds, at least 1 ms, not '{text}'"


def test_a_step_size_without_a_unit_is_milliseconds_as_for_the_server() -> None:
    assert step_size_in_milliseconds(text="900000") == step_size_in_milliseconds(text="15min") == 900_000


def test_a_step_size_of_zero_milliseconds_is_refused_as_by_the_server() -> None:
    with pytest.raises(ArgumentTypeError) as error:
        step_size_in_milliseconds(text="0")

    assert str(error.value) == "must be a whole number of at least 1, not '0'"
