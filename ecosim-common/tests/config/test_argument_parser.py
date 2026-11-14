from ecosim_common.config.app_config import AppConfigParameter, add_parameters
from ecosim_common.config.argument_parser import EcosimArgumentParser


def test_the_help_ends_an_option_with_its_default_but_not_a_flag() -> None:
    parser = EcosimArgumentParser(prog="ecosim-test")
    add_parameters(
        parser=parser,
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
