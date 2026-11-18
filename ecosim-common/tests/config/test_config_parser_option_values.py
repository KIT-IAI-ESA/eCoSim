from argparse import ArgumentTypeError
from typing import Any, Callable

import pytest
from ecosim_common.config.config_parser import ConfigParser


@pytest.mark.parametrize(
    "convert, text, value",
    [
        (ConfigParser.positive_whole_number, "1", 1),
        (ConfigParser.positive_whole_number, "35040", 35040),
        (ConfigParser.port_number, "1", 1),
        (ConfigParser.port_number, "65535", 65535),
        (ConfigParser.number_from_zero_to_one, "0", 0.0),
        (ConfigParser.number_from_zero_to_one, "0.5", 0.5),
        (ConfigParser.number_from_zero_to_one, "1", 1.0),
        (ConfigParser.true_or_false, "True", True),
        (ConfigParser.true_or_false, "no", False),
        (ConfigParser.choice_name, "TCP-SOCKET", "tcp_socket"),
    ],
)
def test_a_valid_text_becomes_its_value(convert: Callable[[str], Any], text: str, value: Any) -> None:
    assert convert(text) == value


@pytest.mark.parametrize(
    "convert, text, message",
    [
        (ConfigParser.positive_whole_number, "abc", "must be a whole number of at least 1, not 'abc'"),
        (ConfigParser.port_number, "70000", "must be a port number from 1 to 65535, not '70000'"),
        (ConfigParser.number_from_zero_to_one, "2", "must be a number from 0 to 1, not '2'"),
        (ConfigParser.true_or_false, "maybe", "must be true or false, not 'maybe'"),
    ],
)
def test_a_bad_text_is_rejected_with_the_rule_and_the_text(convert: Callable[[str], Any], text: str, message: str) -> None:
    with pytest.raises(ArgumentTypeError) as error_info:
        convert(text)

    assert str(error_info.value) == message


@pytest.mark.parametrize(
    "convert, text",
    [
        (ConfigParser.positive_whole_number, "0"),
        (ConfigParser.positive_whole_number, "-3"),
        (ConfigParser.positive_whole_number, "1.5"),
        (ConfigParser.port_number, "0"),
        (ConfigParser.number_from_zero_to_one, "fast"),
        (ConfigParser.number_from_zero_to_one, "nan"),
    ],
)
def test_a_text_outside_the_rule_is_rejected(convert: Callable[[str], Any], text: str) -> None:
    with pytest.raises(ArgumentTypeError):
        convert(text)
