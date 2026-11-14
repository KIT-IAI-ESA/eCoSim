import importlib
import sys
from typing import Sequence

from ecosim_common.tech.close_name import did_you_mean
from ecosim_common.tech.deployment.module_version import get_module_version

from ecosim.command import COMMANDS, Command

USAGE = "usage: ecosim [--version] [--help] COMMAND [OPTIONS]"
# the code argparse ends a wrong command line with
USAGE_ERROR_EXIT_CODE = 2


def main() -> None:
    sys.exit(run_command(arguments=sys.argv[1:]))


def run_command(arguments: Sequence[str]) -> int:
    if not arguments or arguments[0] in ("-h", "--help"):
        print(help_text())
        return 0
    if arguments[0] == "--version":
        print(f"ecosim {get_module_version(name='ecosim')}")
        return 0
    command = next((command for command in COMMANDS if command.name == arguments[0]), None)
    if command is None:
        print(f"{USAGE}\necosim: error: {unknown_command_message(name=arguments[0])}", file=sys.stderr)
        return USAGE_ERROR_EXIT_CODE
    return run(command=command, passed_arguments=arguments[1:])


def run(command: Command, passed_arguments: Sequence[str]) -> int:
    # imported only now, since they take a second to import and ecosim --help needs neither
    from ecosim_common.tech.one_line_errors import exits_with_one_line_errors
    from ecosim_common.tech.shutdown_manager import ShutdownManager

    command_main = exits_with_one_line_errors(program_name=f"ecosim {command.name}")(importlib.import_module(command.module).main)
    try:
        return int(command_main(passed_arguments))
    except KeyboardInterrupt:
        # Ctrl-C before or after a run, during a run the command handles it itself
        return ShutdownManager.INTERRUPT_EXIT_CODE


def unknown_command_message(name: str) -> str:
    names = [command.name for command in COMMANDS]
    # the names of the commands are short and few, so a swap of two letters is close enough
    hint = did_you_mean(name=name, known_names=names, cutoff=0.6) or f" The commands are {', '.join(names)}."
    return f"'{name}' is not a command.{hint}"


def help_text() -> str:
    width = max(len(command.name) for command in COMMANDS)
    return "\n".join(
        [
            USAGE,
            "",
            "Couples simulation models and runs them together.",
            "",
            "commands:",
            *(f"  {command.name.ljust(width)}  {command.summary}" for command in COMMANDS),
            "",
            "Run 'ecosim COMMAND --help' for the options of a command.",
        ],
    )


if __name__ == "__main__":
    main()
