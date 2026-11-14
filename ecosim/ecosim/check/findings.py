from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser, ConfigParserException
from ecosim_common.tech.close_name import closest_name
from ecosim_common.tech.one_line_errors import one_line_message


@dataclass
class Findings:
    """What a check found. A problem stops a run, a warning does not."""

    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add(self, other: Findings) -> None:
        self.problems += other.problems
        self.warnings += other.warnings


def problem_of(error: Exception, file: Path) -> str:
    return with_the_file(message=one_line_message(error=error), file=file)


def with_the_file(message: str, file: Path) -> str:
    """The message after the file, if the message does not name it."""
    return message if str(file) in message or str(file.absolute()) in message else f"{file}: {message}"


def problem_of_ini_file(error: Exception, ini_file: Path) -> str:
    """Like problem_of, with a hint for a missing section or key."""
    problem = problem_of(error=error, file=ini_file)
    if not isinstance(error, ConfigParserException) or error.section is None:
        return problem
    return problem + _hint_for_missing(section=error.section, option=error.option, config_parser=ConfigParser(ini_file))


def _hint_for_missing(section: str, option: str | None, config_parser: ConfigParser) -> str:
    if option is None:
        written = closest_name(name=section, known_names=config_parser.sections())
        # sections are case-sensitive, unlike keys
        return "" if written is None else f". Did you mean [{section}] instead of [{written}]?"
    written = closest_name(name=option, known_names=config_parser.options(section))
    return "" if written is None else f". Did you mean {option} instead of {written}?"
