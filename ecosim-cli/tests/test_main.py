import pytest
from ecosim.command import COMMANDS, Command
from ecosim.main import run_command
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim_common.tech.shutdown_manager import ShutdownManager

from tests.command_errors import error_of


def test_the_help_lists_every_command_with_its_summary(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_command(arguments=["--help"]) == ShutdownManager.SUCCESS_EXIT_CODE

    help_text = capsys.readouterr().out
    assert all(f"  {command.name}" in help_text and command.summary in help_text for command in COMMANDS)


def test_no_command_shows_the_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_command(arguments=[]) == ShutdownManager.SUCCESS_EXIT_CODE

    assert capsys.readouterr().out.startswith("usage: ecosim")


@pytest.mark.parametrize("misspelled, command", [("chekc", "check"), ("rnu", "run"), ("resluts", "results")])
def test_a_misspelled_command_suggests_the_closest_command(misspelled: str, command: str, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, error_line = error_of(arguments=[misspelled, "building"], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line == f"ecosim: error: '{misspelled}' is not a command. Did you mean {command}?"


def test_an_unknown_command_without_a_close_one_lists_the_commands(capsys: pytest.CaptureFixture[str]) -> None:
    _, error_line = error_of(arguments=["simulate"], capsys=capsys)

    assert error_line.endswith(f"The commands are {', '.join(command.name for command in COMMANDS)}.")


@pytest.mark.parametrize("command", COMMANDS, ids=[command.name for command in COMMANDS])
def test_a_wrong_option_of_a_command_is_a_usage_error_of_that_command(command: Command, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, error_line = error_of(arguments=[command.name, "--no-such-option"], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line.startswith(f"ecosim {command.name}: error: ")
