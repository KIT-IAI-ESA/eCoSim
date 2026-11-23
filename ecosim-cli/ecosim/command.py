from dataclasses import dataclass

from ecosim_common.config.argument_parser import EcosimArgumentParser
from ecosim_common.tech.deployment.module_version import get_module_version


@dataclass(frozen=True)
class Command:
    name: str
    summary: str
    # has build_parser() and main(passed_arguments)
    module: str


COMMANDS = (
    Command(name="new", summary="Write a simulation folder from FMUs", module="ecosim.new.new_command"),
    Command(name="check", summary="Check a simulation folder before a run", module="ecosim.check.check_command"),
    Command(name="run", summary="Run a simulation locally", module="ecosim.run.run_command"),
    Command(name="results", summary="Show the results of a run, or write them to a CSV file", module="ecosim.results.results_command"),
)


def command_parser(name: str, description: str, examples: tuple[str, ...]) -> EcosimArgumentParser:
    parser = EcosimArgumentParser(
        prog=f"ecosim {name}",
        usage="%(prog)s [options] [SIMULATION] [-- SERVER OPTIONS]",
        description=description,
        epilog="\n".join(["examples:", *(f"  {example}" for example in examples)]),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {get_module_version(name='ecosim')}")
    return parser
