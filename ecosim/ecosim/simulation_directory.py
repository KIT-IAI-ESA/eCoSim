from __future__ import annotations

import dataclasses
import os
from argparse import Namespace
from dataclasses import dataclass
from pathlib import Path

from ecosim_common.tech.close_name import did_you_mean

from ecosim.report_lines import and_joined, ecosim_program

SIMULATION_CONFIG = Path("server") / "simulation.json"
SIMULATOR_DIR = "modules"
# older simulations have Modules/
OLDER_SIMULATOR_DIR = "Modules"


@dataclass(frozen=True)
class SimulationDirectory:
    path: Path
    simulation_config: Path
    server_config: Path
    simulator_dir: Path

    @staticmethod
    def of_options(options: Namespace) -> SimulationDirectory:
        layout = SimulationDirectory.of_path(path=Path(options.simulation or "."))
        return dataclasses.replace(
            layout,
            simulation_config=Path(options.simulation_config or layout.simulation_config),
            server_config=Path(options.server_config or layout.server_config),
            simulator_dir=Path(options.simulator_dir or layout.simulator_dir),
        )

    @staticmethod
    def of_path(path: Path) -> SimulationDirectory:
        return SimulationDirectory(
            path=path,
            simulation_config=path / SIMULATION_CONFIG,
            server_config=path / "server" / "preferences.ini",
            simulator_dir=SimulationDirectory._simulator_dir_of(path=path),
        )

    @staticmethod
    def _simulator_dir_of(path: Path) -> Path:
        simulator_dir, older_simulator_dir = path / SIMULATOR_DIR, path / OLDER_SIMULATOR_DIR
        return older_simulator_dir if older_simulator_dir.is_dir() and not simulator_dir.is_dir() else simulator_dir

    @property
    def name(self) -> str:
        return self.path.resolve().name

    @property
    def results(self) -> Path:
        return self.path / "results"

    def reason_it_is_not_a_simulation(self, command_name: str, working_directory: Path = Path(".")) -> str | None:
        if self.path.is_file():
            return (
                f"{self.path} is a file, not a simulation folder. "
                + "Pass the folder with server/ and modules/, or pass the file with --simulation-config."
            )
        if not self.path.is_dir():
            return missing_directory_message(directory=self.path)
        if self.simulation_config.is_file():
            return self._reason_of_both_simulator_dirs()
        if self.simulation_config != self.path / SIMULATION_CONFIG:
            return f"the simulation config {self.simulation_config} does not exist"
        return f"{self.name} is not a simulation folder. It has no {SIMULATION_CONFIG}." + hint_to_a_simulation(
            directory=self.path,
            command_name=command_name,
            working_directory=working_directory,
        )

    def _reason_of_both_simulator_dirs(self) -> str | None:
        # on Linux modules/ and Modules/ are two folders, and only modules/ is read
        older_simulator_dir = self.path / OLDER_SIMULATOR_DIR
        if self.simulator_dir != self.path / SIMULATOR_DIR or not older_simulator_dir.is_dir() or older_simulator_dir.samefile(self.simulator_dir):
            return None
        return f"{self.name} has modules/ and Modules/. Move the folders in Modules/ into modules/."


def missing_directory_message(directory: Path) -> str:
    return f"the folder {directory} does not exist.{did_you_mean(name=directory.name, known_names=_directories_next_to(path=directory))}"


def hint_to_a_simulation(directory: Path, command_name: str, working_directory: Path = Path(".")) -> str:
    return _hint_to_the_simulation_above(
        directory=directory,
        command_name=command_name,
        working_directory=working_directory,
    ) or _hint_to_the_simulations_in_it(directory=directory, command_name=command_name, working_directory=working_directory)


def _hint_to_the_simulation_above(directory: Path, command_name: str, working_directory: Path) -> str:
    parent = directory.resolve().parent
    if not (parent / SIMULATION_CONFIG).is_file():
        return ""
    simulation = os.path.relpath(parent, start=working_directory)
    return f" The simulation is the folder above it. Run '{_program_text()} {command_name} {simulation}'."


def _hint_to_the_simulations_in_it(directory: Path, command_name: str, working_directory: Path) -> str:
    simulations = sorted(
        os.path.relpath(simulation, start=working_directory) for simulation in directory.iterdir() if (simulation / SIMULATION_CONFIG).is_file()
    )
    if not simulations:
        return ""
    command = f"'{_program_text()} {command_name} {simulations[0]}'"
    if len(simulations) == 1:
        return f" It contains the simulation {simulations[0]}. Run {command}."
    return f" It contains the simulations {and_joined(texts=simulations)}. Run for example {command}."


def _program_text() -> str:
    return " ".join(ecosim_program())


def _directories_next_to(path: Path) -> list[str]:
    parent = path.absolute().parent
    return [directory.name for directory in parent.iterdir() if directory.is_dir()] if parent.is_dir() else []
