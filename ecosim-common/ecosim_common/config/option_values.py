"""Converters for AppConfigParameter.transform. argparse turns their ArgumentTypeError into a usage error with exit code 2."""

import math
from argparse import ArgumentTypeError

from ecosim_common.config.config_parser import ConfigParser, ConfigParserException


def positive_whole_number(text: str) -> int:
    if not text.strip().isdecimal() or int(text) < 1:
        raise ArgumentTypeError(f"must be a whole number of at least 1, not '{text}'")
    return int(text)


def port_number(text: str) -> int:
    if not text.strip().isdecimal() or not 1 <= int(text) <= 65535:
        raise ArgumentTypeError(f"must be a port number from 1 to 65535, not '{text}'")
    return int(text)


def number_from_zero_to_one(text: str) -> float:
    try:
        number = float(text)
    except ValueError:
        # nan fails the range check below
        number = math.nan
    if not 0 <= number <= 1:
        raise ArgumentTypeError(f"must be a number from 0 to 1, not '{text}'")
    return number


def true_or_false(text: str) -> bool:
    try:
        return ConfigParser.config_string_to_bool(text)
    except ConfigParserException:
        raise ArgumentTypeError(f"must be true or false, not '{text}'") from None


def choice_name(text: str) -> str:
    """Accepts any letter case and a hyphen for the underscore, like TCP_SOCKET or tcp-socket for tcp_socket."""
    return text.strip().lower().replace("-", "_")
