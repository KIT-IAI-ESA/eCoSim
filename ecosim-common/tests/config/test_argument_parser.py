import pytest
from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE, EcosimArgumentParser
from ecosim_common.config.config_parser import ConfigParser
from ecosim_test_common.exit_code_and_error_line import exit_code_and_error_line

PARAMETERS = [
    AppConfigParameter(name="steps", required=True, transform=ConfigParser.positive_whole_number, help_text="steps"),
    AppConfigParameter(name="database-type", transform=ConfigParser.choice_name, choices=("postgres", "file"), help_text="type"),
    AppConfigParameter(name="pace", default_value="1", help_text="pace"),
]


def create_parser_with_parameters() -> EcosimArgumentParser:
    parser = EcosimArgumentParser(prog="ecosim-test")
    parser.add_parameters(parameters=PARAMETERS, environment_variables={})
    return parser


def error_of(parser: EcosimArgumentParser, arguments: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    exit_code, error_line = exit_code_and_error_line(command=lambda: parser.parse_args(arguments), capsys=capsys)
    assert exit_code == USAGE_ERROR_EXIT_CODE
    return error_line


def test_a_misspelled_option_gets_the_closest_option_as_a_hint(capsys: pytest.CaptureFixture[str]) -> None:
    error = error_of(parser=create_parser_with_parameters(), arguments=["--steps", "3", "--databse-type", "file"], capsys=capsys)

    assert error == "ecosim-test: error: unrecognized arguments: --databse-type file. Did you mean --database-type instead of --databse-type?"


def test_a_misspelled_required_option_gets_the_hint_next_to_the_missing_option(capsys: pytest.CaptureFixture[str]) -> None:
    error = error_of(parser=create_parser_with_parameters(), arguments=["--stpes", "3"], capsys=capsys)

    assert error == "ecosim-test: error: the following arguments are required: --steps. Did you mean --steps instead of --stpes?"


def test_an_option_with_no_close_name_gets_no_hint(capsys: pytest.CaptureFixture[str]) -> None:
    error = error_of(parser=create_parser_with_parameters(), arguments=["--steps", "3", "--frobnicate"], capsys=capsys)

    assert error == "ecosim-test: error: unrecognized arguments: --frobnicate"


def test_the_unique_start_of_an_option_name_still_works() -> None:
    assert create_parser_with_parameters().parse_args(["--steps", "3", "--database-t", "file"]).database_type == "file"


def test_a_subcommand_suggests_the_closest_of_its_own_options(capsys: pytest.CaptureFixture[str]) -> None:
    parser = EcosimArgumentParser(prog="ecosim")
    run = parser.add_subparsers(dest="command", required=True).add_parser(name="run")
    run.add_parameters(parameters=PARAMETERS, environment_variables={})

    error = error_of(parser=parser, arguments=["run", "--steps", "3", "--databse-type", "file"], capsys=capsys)

    assert error.startswith("ecosim run: error: ")
    assert "--database-type instead of --databse-type" in error


def test_the_arguments_after_a_double_dash_are_handed_back_as_they_are() -> None:
    _, unknown_arguments = create_parser_with_parameters().parse_known_args(["--steps", "3", "--", "--databse-type", "file"])

    assert unknown_arguments[-2:] == ["--databse-type", "file"]


def test_the_help_ends_an_option_with_its_default_but_not_a_flag() -> None:
    parser = EcosimArgumentParser(prog="ecosim-test")
    parser.add_parameters(
        parameters=[
            AppConfigParameter(name="pace", default_value="1", help_text="The pace."),
            AppConfigParameter(name="debug", is_flag=True, help_text="More logs."),
        ],
        environment_variables={},
    )

    help_text = parser.format_help()

    assert "The pace. Default: 1." in help_text
    assert "More logs.\n" in help_text


def test_the_help_keeps_the_lines_of_the_examples() -> None:
    parser = EcosimArgumentParser(prog="ecosim-test", epilog="examples:\n  ecosim-test --steps 3 \\\n      --pace 0.5")

    assert parser.format_help().endswith("examples:\n  ecosim-test --steps 3 \\\n      --pace 0.5\n")
