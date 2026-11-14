from typing import Sequence

from ecosim_common.config.argument_parser import EcosimArgumentParser

from ecosim.check.check_report import report_lines
from ecosim.check.simulation_check import SimulationCheck
from ecosim.command import command_parser
from ecosim.report_lines import command_text, ecosim_program
from ecosim.simulation_command_line import SimulationCommandLine
from ecosim.simulation_options import add_run_options, add_simulation_options


def build_parser() -> EcosimArgumentParser:
    parser = command_parser(
        name="check",
        description="Checks a simulation before a run: the simulation config, the server config and the folder of every simulator with its model. "
        + "It reads them as a run with the same options would, lists every problem with its file, and names the closest name for a typo. "
        + "It changes nothing and starts nothing. The options after -- are options of ecosim-server, which the check reads as well.",
        examples=(
            "ecosim check building",
            "ecosim check building --duration 365d",
            "ecosim check building_hpc --database-type postgres --steps 100 -- --database-schema run_2",
        ),
    )
    add_simulation_options(parser=parser)
    add_run_options(parser=parser)
    return parser


def main(passed_arguments: Sequence[str]) -> int:
    command_line = SimulationCommandLine.of_arguments(parser=build_parser(), passed_arguments=passed_arguments, command_name="check")
    check = SimulationCheck.of_simulation(simulation=command_line.simulation, run_options=command_line.run_options)
    check_command = command_text(arguments=[*ecosim_program(), "check", *passed_arguments])
    print("\n".join(report_lines(check=check, simulation=command_line.simulation, check_command=check_command)))
    return 1 if check.findings.problems else 0
