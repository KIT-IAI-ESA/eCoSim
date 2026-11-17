"""Read the options of a command from its argparse parser."""

import argparse
from dataclasses import dataclass, field
from functools import partial
from typing import Any, Iterable, override


@dataclass(frozen=True)
class Option:
    name: str
    value: str
    required: bool
    flag: bool
    default: Any
    help: str


@dataclass(frozen=True)
class Section:
    title: str
    options: list[Option] = field(default_factory=list)


class SectionRecorder(argparse.HelpFormatter):
    """Records the options of each section while argparse formats the help."""

    def __init__(self, prog: str, sections: list[Section]) -> None:
        super().__init__(prog=prog)
        self._sections = sections

    @override
    def start_section(self, heading: str | None) -> None:
        super().start_section(heading)
        self._sections.append(Section(title=heading or ""))

    @override
    def add_arguments(self, actions: Iterable[argparse.Action]) -> None:
        super().add_arguments(actions)
        self._sections[-1].options.extend(to_option(action) for action in actions if action.dest not in ("help", "version"))


def collect_sections(parser: argparse.ArgumentParser) -> list[Section]:
    """Return the sections of the help with their options, without --help and --version."""
    sections: list[Section] = []
    parser.formatter_class = partial(SectionRecorder, sections=sections)
    parser.format_help()
    return [section for section in sections if section.options]


def to_option(action: argparse.Action) -> Option:
    if not action.option_strings:
        return Option(name=value_name(action), value="", required=action.required, flag=False, default=action.default, help=help_of(action))
    flag = action.nargs == 0
    return Option(
        name=action.option_strings[-1],
        value="" if flag else value_name(action),
        required=action.required,
        flag=flag,
        default=action.default,
        help=help_of(action),
    )


def help_of(action: argparse.Action) -> str:
    # argparse help texts write a literal % as %%
    return (action.help or "").replace("%%", "%")


def value_name(action: argparse.Action) -> str:
    """Return the value as --help shows it."""
    if action.metavar is not None:
        return str(action.metavar)
    if action.choices is not None:
        return "{" + ",".join(map(str, action.choices)) + "}"
    return action.dest.upper()
