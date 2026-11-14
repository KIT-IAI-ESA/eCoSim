import importlib

import pytest
from ecosim.command import COMMANDS, Command
from ecosim.main import run_command


def test_the_help_lists_every_command_with_its_summary(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_command(arguments=["--help"]) == 0

    help_text = capsys.readouterr().out
    assert all(f"  {command.name}" in help_text and command.summary in help_text for command in COMMANDS)


def test_no_command_shows_the_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_command(arguments=[]) == 0

    assert capsys.readouterr().out.startswith("usage: ecosim")


def test_a_misspelt_command_names_the_closest_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_command(arguments=["chekc", "building"]) == 2

    assert capsys.readouterr().err.splitlines()[-1] == "ecosim: error: 'chekc' is not a command. Did you mean check?"


def test_an_unknown_command_without_a_close_one_lists_the_commands(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_command(arguments=["simulate"]) == 2

    assert (
        capsys.readouterr().err.splitlines()[-1]
        == f"ecosim: error: 'simulate' is not a command. The commands are {', '.join(command.name for command in COMMANDS)}."
    )


@pytest.mark.parametrize("command", COMMANDS, ids=[command.name for command in COMMANDS])
def test_every_command_has_a_parser_named_after_it_and_a_main(command: Command) -> None:
    module = importlib.import_module(command.module)

    assert module.build_parser().prog == f"ecosim {command.name}"
    assert callable(module.main)


def test_a_wrong_option_of_a_command_ends_in_one_line_with_the_name_of_the_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        run_command(arguments=["check", "--steps", "0"])

    assert exit_info.value.code == 2
    assert capsys.readouterr().err.splitlines()[-1] == "ecosim check: error: argument --steps: must be a whole number of at least 1, not '0'"
