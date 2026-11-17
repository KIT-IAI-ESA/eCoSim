from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Sequence

from ecosim_common.config import config_parser
from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.config.console_script import ConsoleScript


class AppConfig(object):
    """
    This class bootstraps the app configuration. In general, it adds all given parameters as CLI arguments. All CLI arguments can optionally
    have default values that optionally can be overridden by environment variables.

    A given CLI argument has a higher priority than an environment variable.

    So the implicit priority is:  CLI argument > Environment variable > Default value
    """

    def __init__(
        self,
        console_script: ConsoleScript,
        parameters: Sequence[AppConfigParameter],
        environment_variables: Mapping[str, str] | None = None,
        passed_arguments: Sequence[str] | None = None,
    ) -> None:
        parser = create_parser(
            console_script=console_script,
            parameters=parameters,
            environment_variables=os.environ if environment_variables is None else environment_variables,
        )
        # None reads sys.argv
        self._args = parser.parse_args(passed_arguments)


def create_parser(
    console_script: ConsoleScript,
    parameters: Sequence[AppConfigParameter],
    environment_variables: Mapping[str, str],
) -> EcosimArgumentParser:
    parser = EcosimArgumentParser(
        prog=console_script.name,
        usage=short_usage(parameters),
        description=console_script.description,
        epilog=console_script.examples_text(),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {console_script.version()}")
    add_parameters(parser=parser, parameters=parameters, environment_variables=environment_variables)
    return parser


def add_parameters(
    parser: argparse.ArgumentParser,
    parameters: Iterable[AppConfigParameter],
    environment_variables: Mapping[str, str],
) -> None:
    parameters_by_group: dict[str | None, list[AppConfigParameter]] = {}
    for parameter in parameters:
        parameters_by_group.setdefault(parameter.group, []).append(parameter)
    for group, grouped_parameters in parameters_by_group.items():
        container = parser if group is None else parser.add_argument_group(title=group)
        for parameter in grouped_parameters:
            container.add_argument(parameter.to_cli_variable(), **parameter.argparse_settings(environment_variables))


def short_usage(parameters: Iterable[AppConfigParameter]) -> str:
    required = [
        f"{parameter.to_cli_variable()} {parameter.metavar or parameter.to_parsed_arg_name().upper()}"
        for parameter in parameters
        if parameter.required
    ]
    return " ".join(["%(prog)s", *required, "[options]"])


@dataclass(frozen=True)
class AppConfigParameter:
    name: str
    help_text: str
    # set if it is a flag parameter (i.e. a parameter without a value - the parameter is 'True' if it exists, 'False' if it does not exist)
    is_flag: bool = False
    required: bool = False
    enable_environment_variable: bool = False
    environment_variable_prefix: str | None = None
    default_value: str | None = None
    # argparse turns an ArgumentTypeError of the transform into a usage error
    transform: Callable[[str], Any] | None = None
    # argparse compares them with the value after the transform
    choices: tuple[str, ...] | None = None
    metavar: str | None = None
    group: str | None = None

    def to_environment_variable(self) -> str:
        name = self.name.replace("-", "_").upper()
        if self.environment_variable_prefix is None:
            return name
        return f"{self.environment_variable_prefix}{name}"

    def to_cli_variable(self) -> str:
        return f"--{self.name}"

    def to_parsed_arg_name(self) -> str:
        return self.name.replace("-", "_")

    def argparse_settings(self, environment_variables: Mapping[str, str]) -> dict[str, Any]:
        if self.is_flag:
            return {"action": "store_true", "default": self._flag_default(environment_variables), "help": self.help_text}
        return {
            "required": self.required,
            "default": self._default(environment_variables),
            "type": self.transform,
            "choices": self.choices,
            "metavar": self.metavar,
            "help": self.help_text,
        }

    def _default(self, environment_variables: Mapping[str, str]) -> str | None:
        if self.enable_environment_variable and self.to_environment_variable() in environment_variables:
            return environment_variables[self.to_environment_variable()]
        return self.default_value

    def _flag_default(self, environment_variables: Mapping[str, str]) -> bool:
        if self.enable_environment_variable and self.to_environment_variable() in environment_variables:
            return True
        return config_parser.ConfigParser.config_string_to_bool(self.default_value or "False")
