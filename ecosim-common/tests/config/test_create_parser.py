from importlib.metadata import version

import pytest
from ecosim_common.config.app_config import AppConfigParameter, create_parser

from tests.config.console_script_test_setup import CONSOLE_SCRIPT


def test_version_prints_the_name_and_the_version_of_the_package(capsys: pytest.CaptureFixture[str]) -> None:
    parser = create_parser(console_script=CONSOLE_SCRIPT, parameters=[], environment_variables={})

    with pytest.raises(SystemExit) as exit_info:
        parser.parse_args(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"ecosim-common {version('ecosim-common')}\n"


def test_the_usage_line_shows_only_the_required_options() -> None:
    parser = create_parser(
        console_script=CONSOLE_SCRIPT,
        parameters=[
            AppConfigParameter(name="config-file", required=True, metavar="FILE", help_text="config"),
            AppConfigParameter(name="debug", is_flag=True, help_text="debug"),
        ],
        environment_variables={},
    )

    assert parser.format_usage() == "usage: ecosim-common --config-file FILE [options]\n"


def test_the_help_lists_each_option_under_the_title_of_its_group() -> None:
    parser = create_parser(
        console_script=CONSOLE_SCRIPT,
        parameters=[
            AppConfigParameter(name="debug", is_flag=True, help_text="debug"),
            AppConfigParameter(name="steps", group="run", metavar="N", help_text="steps"),
        ],
        environment_variables={},
    )

    help_text = parser.format_help()

    assert help_text.index("\noptions:\n") < help_text.index("  --debug") < help_text.index("\nrun:\n  --steps N")
