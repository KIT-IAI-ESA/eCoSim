from datetime import datetime
from ecosim_common.config.app_config import AppConfig, AppConfigParameter


def test_app_config_defaults() -> None:
    app_config = AppConfig(
        passed_arguments=[],
        environment_variables={},
        cli_description="CLI description",
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
        cli_description="CLI description",
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
        cli_description="CLI description",
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
        cli_description="CLI description",
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
        cli_description="CLI description",
        parameters=[
            AppConfigParameter(
                name="value-override",
                default_value="222",
                help_text="simple test",
            ),
        ],
    )
    assert app_config._args.value_override == "333"
