from argparse import ArgumentTypeError
from typing import Any, Callable

import pytest
from ecosim_common.config.option_values import choice_name, number_from_zero_to_one, port_number, positive_whole_number, true_or_false


@pytest.mark.parametrize(
    "convert, text, value",
    [
        (positive_whole_number, "1", 1),
        (positive_whole_number, "35040", 35040),
        (port_number, "1", 1),
        (port_number, "65535", 65535),
        (number_from_zero_to_one, "0", 0.0),
        (number_from_zero_to_one, "0.5", 0.5),
        (number_from_zero_to_one, "1", 1.0),
        (true_or_false, "True", True),
        (true_or_false, "no", False),
        (choice_name, "TCP-SOCKET", "tcp_socket"),
    ],
)
def test_a_valid_text_becomes_its_value(convert: Callable[[str], Any], text: str, value: Any) -> None:
    assert convert(text) == value


@pytest.mark.parametrize(
    "convert, text, message",
    [
        (positive_whole_number, "abc", "must be a whole number of at least 1, not 'abc'"),
        (positive_whole_number, "0", "must be a whole number of at least 1, not '0'"),
        (positive_whole_number, "-3", "must be a whole number of at least 1, not '-3'"),
        (positive_whole_number, "1.5", "must be a whole number of at least 1, not '1.5'"),
        (port_number, "0", "must be a port number from 1 to 65535, not '0'"),
        (port_number, "70000", "must be a port number from 1 to 65535, not '70000'"),
        (number_from_zero_to_one, "2", "must be a number from 0 to 1, not '2'"),
        (number_from_zero_to_one, "fast", "must be a number from 0 to 1, not 'fast'"),
        (number_from_zero_to_one, "nan", "must be a number from 0 to 1, not 'nan'"),
        (true_or_false, "maybe", "must be true or false, not 'maybe'"),
    ],
)
def test_a_bad_text_is_rejected_with_the_rule_and_the_text(convert: Callable[[str], Any], text: str, message: str) -> None:
    with pytest.raises(ArgumentTypeError) as error_info:
        convert(text)

    assert str(error_info.value) == message
