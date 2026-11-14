import argparse
import textwrap
from typing import Any, override


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
    """An ArgumentParser with the help layout of every eCoSim command. Subcommands get the same class."""

    def __init__(self, **settings: Any) -> None:
        settings.setdefault("formatter_class", EcosimHelpFormatter)
        super().__init__(**settings)
