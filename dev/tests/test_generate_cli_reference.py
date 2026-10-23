import argparse

from generate_cli_reference import Option, collect_options, render_page, render_row


def build_sample() -> object:
    parser = argparse.ArgumentParser(description="sample")
    parser.add_argument("--config-file", required=True, help="Path to the config file.")
    parser.add_argument("--debug", action="store_true", default=False, help="More logs")
    parser.add_argument("--pace", default="1.0", help="Pace, 1 means 100%%")
    return parser.parse_args()


def test_collect_options_records_every_option_except_help() -> None:
    options = collect_options(build_sample)

    assert [option.name for option in options] == ["config-file", "debug", "pace"]
    assert options[0].required
    assert options[1].flag
    assert options[2] == Option("pace", False, False, "1.0", "Pace, 1 means 100%")


def test_collect_options_restores_argparse() -> None:
    before = argparse.ArgumentParser.add_argument

    collect_options(build_sample)

    assert argparse.ArgumentParser.add_argument is before


def test_render_row() -> None:
    assert render_row(Option("pace", False, False, "1.0", "a | b")) == "| `--pace` |  | `1.0` | a \\| b |"
    assert render_row(Option("debug", False, True, False, "x")) == "| `--debug` |  | flag | x |"
    assert render_row(Option("steps", True, False, None, "n")) == "| `--steps` | yes |  | n |"


def test_render_page_has_one_table_per_command() -> None:
    page = render_page([("Server", "ecosim-server", "Starts the server.", [Option("steps", True, False, None, "n")])])

    assert "## Server" in page
    assert "`ecosim-server`" in page
    assert "| `--steps` | yes |  | n |" in page
