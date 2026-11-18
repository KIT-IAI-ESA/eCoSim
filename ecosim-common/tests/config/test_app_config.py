from datetime import datetime

import pytest
from ecosim_common.config.app_config import AppConfig, AppConfigParameter
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim_common.config.config_parser import ConfigParser

from tests.config.console_script_test_setup import CONSOLE_SCRIPT

# ruff: noqa: SLF001  # a lot of tests inspect internal data of app_config -> so access to internal data is not restricted


def test_app_config_defaults() -> None:
    app_config = AppConfig(
        passed_arguments=[],
        environment_variables={},
        console_script=CONSOLE_SCRIPT,
        parameters=[
            AppConfigParameter(
                name="simple-string",
                required=False,
                help_text="a simple string",
            ),
            AppConfigParameter(
                name="string-with-default-value",
                required=False,
                help_text="a simple string",
                default_value="Hello world",
            ),
            AppConfigParameter(
                name="int-value",
                required=False,
                help_text="a simple string",
                default_value="123",
                transform=lambda x: int(x),
            ),
            AppConfigParameter(
                name="transform-to-obj",
                required=False,
                help_text="a simple string",
                default_value="1737028198",
                transform=lambda x: datetime.fromtimestamp(int(x)),
            ),
        ],
    )

    assert app_config._args.simple_string is None
    assert app_config._args.string_with_default_value == "Hello world"
    assert app_config._args.int_value == 123
    assert app_config._args.transform_to_obj == datetime.fromtimestamp(1737028198)


def test_app_config_overwrites() -> None:
    app_config = AppConfig(
        passed_arguments=[],
        environment_variables={"STRING_WITH_DEFAULT_VALUE": "override"},
        console_script=CONSOLE_SCRIPT,
        parameters=[
            AppConfigParameter(
                name="string-with-default-value",
                required=False,
                help_text="a simple string",
                default_value="Hello world",
                enable_environment_variable=True,
            ),
        ],
    )
    assert app_config._args.string_with_default_value == "override"


def test_app_config_transform_none() -> None:
    app_config = AppConfig(
        passed_arguments=[],
        console_script=CONSOLE_SCRIPT,
        parameters=[
            AppConfigParameter(
                name="transform",
                required=False,
                help_text="a simple string",
                transform=lambda x: int(x),
            ),
        ],
    )
    assert app_config._args.transform is None


def test_app_config_flags() -> None:
    app_config = AppConfig(
        passed_arguments=["--flag-required"],
        environment_variables={},
        console_script=CONSOLE_SCRIPT,
        parameters=[
            AppConfigParameter(
                name="flag-required",
                is_flag=True,
                help_text="a simple flag",
            ),
            AppConfigParameter(
                name="flag-absent",
                is_flag=True,
                help_text="a simple flag",
            ),
        ],
    )
    assert app_config._args.flag_required is True
    assert app_config._args.flag_absent is False


def test_app_config_passed_argument_override() -> None:
    app_config = AppConfig(
        passed_arguments=["--value-override", "333"],
        console_script=CONSOLE_SCRIPT,
        parameters=[
            AppConfigParameter(
                name="value-override",
                default_value="222",
                help_text="simple test",
            ),
        ],
    )
    assert app_config._args.value_override == "333"


def test_a_value_the_transform_rejects_ends_in_a_short_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        AppConfig(
            passed_arguments=["--steps", "abc"],
            console_script=CONSOLE_SCRIPT,
            parameters=[AppConfigParameter(name="steps", transform=ConfigParser.positive_whole_number, help_text="steps")],
        )

    assert exit_info.value.code == USAGE_ERROR_EXIT_CODE
    assert capsys.readouterr().err.splitlines() == [
        "usage: ecosim-common [options]",
        "ecosim-common: error: argument --steps: must be a whole number of at least 1, not 'abc'",
    ]


def test_a_choice_is_accepted_in_any_letter_case() -> None:
    app_config = AppConfig(
        passed_arguments=["--protocol", "TCP-SOCKET"],
        console_script=CONSOLE_SCRIPT,
        parameters=[AppConfigParameter(name="protocol", transform=ConfigParser.choice_name, choices=("dask", "tcp_socket"), help_text="protocol")],
    )

    assert app_config._args.protocol == "tcp_socket"
