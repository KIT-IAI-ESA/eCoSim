from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, List

from ecosim_common.config import config_parser


class AppConfig(object):
    """
    This class bootstraps the app configuration. In general, it adds all given parameters as CLI arguments. All CLI arguments can optionally
    have default values that optionally can be overridden by environment variables.

    A given CLI argument has a higher priority than an environment variable.

    So the implicit priority is:  CLI argument > Environment variable > Default value
    """

    def __init__(
        self,
        cli_description: str,
        parameters: List[AppConfigParameter],
        environment_variables: dict[str, str] | None = None,
        passed_arguments: List[Any] | None = None,
        ignore_unknown_arguments: bool = False,
    ):
        if environment_variables is None:
            environment_variables = dict(os.environ)
        if passed_arguments is None:
            passed_arguments = sys.argv[1:]
        else:
            passed_arguments = AppConfig.clean_test_arguments(passed_arguments)  # not an ideal solution but it works for now
        self._parser = argparse.ArgumentParser(description=cli_description)
        for parameter in parameters:
            if parameter.is_flag is False:
                self._add_string(environment_variables, parameter)
            else:
                self._add_flag(environment_variables, parameter)
        self._args: Any
        if ignore_unknown_arguments:
            self._args = self._parser.parse_known_args(passed_arguments)[0]
        else:
            self._args = self._parser.parse_args(passed_arguments)
        for parameter in parameters:
            if not parameter.transform or getattr(self._args, parameter.to_parsed_arg_name()) is None:
                continue
            setattr(
                self._args,
                parameter.to_parsed_arg_name(),
                parameter.transform(getattr(self._args, parameter.to_parsed_arg_name())),
            )

    def _add_string(
        self,
        overrides: dict[str, str],
        parameter: AppConfigParameter,
    ) -> None:
        string_value: str | None = None
        if parameter.enable_environment_variable:
            string_value = overrides.get(parameter.to_environment_variable())
        if string_value is None:
            string_value = parameter.default_value
        self._parser.add_argument(
            parameter.to_cli_variable(),
            type=str,
            required=parameter.required,
            help=parameter.help_text,
            default=string_value,
        )

    def _add_flag(
        self,
        overrides: dict[str, str],
        parameter: AppConfigParameter,
    ) -> None:
        default_value: bool | None = None
        if parameter.enable_environment_variable:
            default_value = parameter.to_environment_variable() in overrides
        default_value = default_value or config_parser.ConfigParser.config_string_to_bool(
            parameter.default_value or "False",
        )
        self._parser.add_argument(
            parameter.to_cli_variable(),
            help=parameter.help_text,
            default=default_value,
            action="store_true",
        )

    @staticmethod
    def clean_test_arguments(passed_arguments: List[Any]) -> List[Any]:
        return [arg for arg in passed_arguments if type(arg) is not str or (not arg.startswith("test/") and arg != "--jb-swapdiff")]


@dataclass
class AppConfigParameter:
    name: str
    help_text: str
    # set if it is a flag parameter (i.e. a parameter without a value - the parameter is 'True' if it exists, 'False' if it does not exist)
    is_flag: bool = False
    required: bool = False
    enable_environment_variable: bool = False
    environment_variable_prefix: str | None = None
    default_value: str | None = None
    transform: Callable[[str], Any] | None = None

    def to_environment_variable(self) -> str:
        name = self.name.replace("-", "_").upper()
        if self.environment_variable_prefix is None:
            return name
        return f"{self.environment_variable_prefix}{name}"

    def to_cli_variable(self) -> str:
        return f"--{self.name}"

    def to_parsed_arg_name(self) -> str:
        return self.name.replace("-", "_")
