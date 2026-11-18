import argparse

from cli_reference.commands import Command
from cli_reference.options import Option, collect_sections
from generate_cli_reference import examples_of, render_command, render_row


def create_sample_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecosim-test",
        description="Tests.",
        epilog="examples:\n  ecosim-test --config-file a.ini \\\n      --debug",
    )
    parser.add_argument("--version", action="version", version="1.0")
    parser.add_argument("--debug", action="store_true", default=False, help="More logs")
    files = parser.add_argument_group("config files")
    files.add_argument("--config-file", required=True, metavar="FILE", help="Path to the config file.")
    run = parser.add_argument_group("run")
    run.add_argument("--pace", default="1", metavar="NUMBER", help="Pace, 1 means 100%%")
    run.add_argument("--database-type", choices=["postgres", "file"], help="Type")
    return parser


def test_the_options_of_argument_groups_are_collected_under_their_titles() -> None:
    sections = collect_sections(create_sample_parser())

    assert [(section.title, [option.name for option in section.options]) for section in sections] == [
        ("options", ["--debug"]),
        ("config files", ["--config-file"]),
        ("run", ["--pace", "--database-type"]),
    ]


def test_an_option_keeps_how_the_help_shows_its_value_and_its_default() -> None:
    run = collect_sections(create_sample_parser())[-1]

    assert run.options == [
        Option(name="--pace", value="NUMBER", required=False, flag=False, default="1", help="Pace, 1 means 100%"),
        Option(name="--database-type", value="{postgres,file}", required=False, flag=False, default=None, help="Type"),
    ]


def test_a_positional_argument_is_written_without_dashes() -> None:
    parser = argparse.ArgumentParser(prog="ecosim run")
    parser.add_argument("study", metavar="STUDY", help="The study folder.")

    positional = collect_sections(parser)[0].options[0]

    assert render_row(positional) == "| `STUDY` | yes |  | The study folder. |"


def test_render_row() -> None:
    pace = Option(name="--pace", value="NUMBER", required=False, flag=False, default="1", help="a | b")
    debug = Option(name="--debug", value="", required=False, flag=True, default=False, help="x")
    steps = Option(name="--steps", value="N", required=True, flag=False, default=None, help="n")

    assert render_row(pace) == "| `--pace NUMBER` |  | `1` | a \\| b |"
    assert render_row(debug) == "| `--debug` |  | flag | x |"
    assert render_row(steps) == "| `--steps N` | yes |  | n |"


def test_the_examples_keep_their_continuation_lines() -> None:
    assert examples_of(create_sample_parser().epilog) == ["ecosim-test --config-file a.ini \\", "    --debug"]


def test_a_command_has_its_description_its_examples_and_a_table_for_each_section() -> None:
    lines = render_command(
        command=Command(title="Test", console_script_modules=[], arguments="", note="See the guide."),
        parsers=[create_sample_parser()],
    )

    assert lines[:4] == ["## Test", "", "`ecosim-test`: Tests.", ""]
    assert "See the guide." in lines
    assert lines[lines.index("```shell") + 1] == "ecosim-test --config-file a.ini \\"
    assert lines[lines.index("**Config files**") + 4] == "| `--config-file FILE` | yes |  | Path to the config file. |"
