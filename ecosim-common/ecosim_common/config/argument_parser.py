import argparse
import sys
import textwrap
from typing import Any, Iterable, NoReturn, override

from ecosim_common.tech.close_name import closest_name

# argparse exits with this code after a usage error
USAGE_ERROR_EXIT_CODE = 2


class EcosimHelpFormatter(argparse.HelpFormatter):
    """Keeps indented example lines as they are and adds the default to the help of an option."""

    @override
    def _fill_text(self, text: str, width: int, indent: str) -> str:
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
    """Adds the closest option to the error of a misspelled option."""

    def __init__(self, **settings: Any) -> None:
        settings.setdefault("formatter_class", EcosimHelpFormatter)
        if sys.version_info >= (3, 14):
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
        # argparse hands a misspelled option of a subcommand back as unknown
        if self._misspelled_option_names(arguments=unknown_arguments):
            self.error(f"unrecognized arguments: {' '.join(unknown_arguments)}")
        return parsed, unknown_arguments

    @override
    def error(self, message: str) -> NoReturn:
        hints = [f"{closest} instead of {misspelled}" for misspelled, closest in self._misspelled_option_names(arguments=self._arguments).items()]
        if hints:
            message = f"{message}. Did you mean {' and '.join(hints)}?"
        super().error(message)

    def _misspelled_option_names(self, arguments: list[str]) -> dict[str, str]:
        if self._subparsers is not None:
            return {}
        option_names = list(self._option_string_actions)
        options_part = arguments[: arguments.index("--")] if "--" in arguments else arguments
        given_names = dict.fromkeys(argument.split("=")[0] for argument in options_part if argument.startswith("-"))
        # argparse accepts a unique start of an option name
        unknown_names = [name for name in given_names if not any(option_name.startswith(name) for option_name in option_names)]
        return {name: closest for name in unknown_names if (closest := closest_name(name=name, known_names=option_names)) is not None}
