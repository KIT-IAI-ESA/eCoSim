from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Sequence

from ecosim.server_arguments import ensure_the_server_takes, reason_to_reject, split_server_options
from ecosim.simulation_directory import SimulationDirectory
from ecosim.simulation_options import RunOptions


@dataclass(frozen=True)
class SimulationCommandLine:
    options: argparse.Namespace
    simulation: SimulationDirectory
    run_options: RunOptions

    @staticmethod
    def of_arguments(parser: argparse.ArgumentParser, passed_arguments: Sequence[str], command_name: str) -> SimulationCommandLine:
        own_arguments, server_options = split_server_options(passed_arguments=passed_arguments)
        options = parser.parse_args(own_arguments)
        simulation = SimulationDirectory.of_options(options=options)
        reason = simulation.reason_it_is_not_a_simulation(command_name=command_name) or reason_to_reject(
            server_options=server_options,
            command_name=command_name,
            command_options=options,
        )
        if reason is not None:
            parser.error(reason)
        ensure_the_server_takes(server_options=server_options, command_parser=parser)
        try:
            run_options = RunOptions.of_options(options=options, server_options=server_options, simulation_config_file=simulation.simulation_config)
        except argparse.ArgumentTypeError as error:
            parser.error(str(error))
        return SimulationCommandLine(options=options, simulation=simulation, run_options=run_options)
