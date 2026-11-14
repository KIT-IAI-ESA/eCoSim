from __future__ import annotations

import os
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

from ecosim_common.tech.close_name import did_you_mean

from ecosim.report_lines import ecosim_program

SIMULATION_CONFIG = Path("server") / "simulation.json"


@dataclass(frozen=True)
class SimulationFolder:
    """The files of a simulation, in the layout of the examples unless an option names a file."""

    path: Path
    simulation_config: Path
    server_config: Path
    simulator_dir: Path

    @staticmethod
    def of_options(options: Namespace) -> SimulationFolder:
        path = Path(options.simulation or ".")
        return SimulationFolder(
            path=path,
            simulation_config=Path(options.simulation_config or path / SIMULATION_CONFIG),
            server_config=Path(options.server_config or path / "server" / "preferences.ini"),
            simulator_dir=Path(options.simulator_dir or path / "Modules"),
        )

    @property
    def name(self) -> str:
        # the name of the folder instead of '.' or '..'
        return self.path.resolve().name

    @property
    def results(self) -> Path:
        return self.path / "results"

    def reason_it_is_no_simulation(self, command_name: str) -> str | None:
        """Why a command cannot use the folder, None if it can."""
        if self.path.is_file():
            return (
                f"{self.path} is a file, not a simulation folder. "
                + "Give the folder that holds server/ and Modules/, or the file with --simulation-config."
            )
        if not self.path.is_dir():
            return missing_folder_message(folder=self.path)
        if self.simulation_config.is_file():
            return None
        if self.simulation_config != self.path / SIMULATION_CONFIG:
            return f"the simulation config {self.simulation_config} does not exist"
        return f"{self.name} is not a simulation folder: it has no {SIMULATION_CONFIG}." + hint_to_a_simulation(
            folder=self.path,
            command_name=command_name,
        )


def missing_folder_message(folder: Path) -> str:
    return f"the folder {folder} does not exist.{did_you_mean(name=folder.name, known_names=_folders_next_to(path=folder))}"


def hint_to_a_simulation(folder: Path, command_name: str) -> str:
    """The simulation above the folder or the simulations in it, empty if there is none."""
    return _hint_to_the_simulation_above(folder=folder, command_name=command_name) or _hint_to_the_simulations_in_it(
        folder=folder,
        command_name=command_name,
    )


def _hint_to_the_simulation_above(folder: Path, command_name: str) -> str:
    # users of the old quick start are in building/Executable
    parent = folder.resolve().parent
    if not (parent / SIMULATION_CONFIG).is_file():
        return ""
    return f" The simulation is the folder above it, so run '{_program_text()} {command_name} {os.path.relpath(parent)}'."


def _hint_to_the_simulations_in_it(folder: Path, command_name: str) -> str:
    simulations = sorted(os.path.relpath(simulation) for simulation in folder.iterdir() if (simulation / SIMULATION_CONFIG).is_file())
    if not simulations:
        return ""
    command = f"'{_program_text()} {command_name} {simulations[0]}'"
    if len(simulations) == 1:
        return f" It holds the simulation {simulations[0]}, so run {command}."
    return f" It holds the simulations {', '.join(simulations[:-1])} and {simulations[-1]}, so run for example {command}."


def _program_text() -> str:
    return " ".join(ecosim_program())


def _folders_next_to(path: Path) -> list[str]:
    parent = path.absolute().parent
    return [folder.name for folder in parent.iterdir() if folder.is_dir()] if parent.is_dir() else []
