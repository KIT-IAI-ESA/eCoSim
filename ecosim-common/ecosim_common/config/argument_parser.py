import argparse
import sys
import textwrap
from typing import Any, Iterable, NoReturn, override

from ecosim_common.tech.close_name import closest_name


class EcosimHelpFormatter(argparse.HelpFormatter):
    """Keeps the example lines as they are and ends the help of an option with its default, if it has one."""

    @override
    def _fill_text(self, text: str, width: int, indent: str) -> str:
        # wrapping an indented example would break the command in the middle
        return "\n".join(
            line if line.startswith(" ") else textwrap.fill(text=line, width=width, initial_indent=indent, subsequent_indent=indent)
            for line in text.splitlines()
        )

    @override
    def _get_help_string(self, action: argparse.Action) -> str | None:
        if action.help is None or action.default in (None, False, argparse.SUPPRESS):
            return action.help
        return f"{action.help} Default: %(default)s."


class EcosimArgumentParser(argparse.ArgumentParser):
    """An ArgumentParser with the eCoSim help layout, whose errors name the closest option for a misspelt one. Subcommands get the same class."""

    def __init__(self, **settings: Any) -> None:
        settings.setdefault("formatter_class", EcosimHelpFormatter)
        if sys.version_info >= (3, 14):
            # names the closest value of a misspelt choice, Python 3.13 and older reject this setting
            settings.setdefault("suggest_on_error", True)
        super().__init__(**settings)
        self._arguments: list[str] = []

    @override
    def parse_known_args(
        self,
        args: Iterable[str] | None = None,
        namespace: Any = None,
    ) -> tuple[Any, list[str]]:
        self._arguments = list(sys.argv[1:] if args is None else args)
        parsed, unknown_arguments = super().parse_known_args(args=self._arguments, namespace=namespace)
        # argparse hands a misspelt option back as unknown, so a subcommand reports it here with its own name and options
        if self._misspelt_option_names(arguments=unknown_arguments):
            self.error(f"unrecognized arguments: {' '.join(unknown_arguments)}")
        return parsed, unknown_arguments

    @override
    def error(self, message: str) -> NoReturn:
        hints = [f"{closest} instead of {misspelt}" for misspelt, closest in self._misspelt_option_names(arguments=self._arguments).items()]
        if hints:
            message = f"{message}. Did you mean {' and '.join(hints)}?"
        super().error(message)

    def _misspelt_option_names(self, arguments: list[str]) -> dict[str, str]:
        if self._subparsers is not None:
            return {}
        option_names = list(self._option_string_actions)
        # what follows -- is not an option of this parser
        options_part = arguments[: arguments.index("--")] if "--" in arguments else arguments
        given_names = dict.fromkeys(argument.split("=")[0] for argument in options_part if argument.startswith("-"))
        # a unique start of an option name is valid, an ambiguous one gets the error of argparse
        unknown_names = [name for name in given_names if not any(option_name.startswith(name) for option_name in option_names)]
        return {name: closest for name in unknown_names if (closest := closest_name(name=name, known_names=option_names)) is not None}
