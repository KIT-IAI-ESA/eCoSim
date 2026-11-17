import os
from argparse import Namespace
from pathlib import Path

from ecosim.simulation_directory import SimulationDirectory
from ecosim_test_common.test_data.building_simulation import write_building_simulation


def simulation_of(simulation: Path, **files: Path) -> SimulationDirectory:
    options = {"simulation_config": None, "server_config": None, "simulator_dir": None, **files}
    return SimulationDirectory.of_options(options=Namespace(simulation=simulation, **options))


def test_the_files_of_a_simulation_are_in_the_layout_of_the_examples(tmp_path: Path) -> None:
    simulation = simulation_of(simulation=tmp_path)

    assert (simulation.simulation_config, simulation.server_config, simulation.simulator_dir, simulation.results) == (
        tmp_path / "server" / "simulation.json",
        tmp_path / "server" / "preferences.ini",
        tmp_path / "Modules",
        tmp_path / "results",
    )


def test_the_files_of_a_simulation_can_be_given_one_by_one(tmp_path: Path) -> None:
    simulation = simulation_of(simulation=tmp_path, simulation_config=Path("run.json"), simulator_dir=Path("simulators"))

    assert (simulation.simulation_config, simulation.server_config, simulation.simulator_dir) == (
        Path("run.json"),
        tmp_path / "server" / "preferences.ini",
        Path("simulators"),
    )


def test_a_simulation_directory_with_a_simulation_config_can_be_used(tmp_path: Path) -> None:
    simulation = simulation_of(simulation=write_building_simulation(directory=tmp_path / "building"))

    assert simulation.reason_it_is_not_a_simulation(command_name="check") is None


def test_a_misspelled_simulation_directory_suggests_the_closest_directory(tmp_path: Path) -> None:
    write_building_simulation(directory=tmp_path / "building")

    reason = simulation_of(simulation=tmp_path / "buildng").reason_it_is_not_a_simulation(command_name="check")

    assert reason == f"the folder {tmp_path / 'buildng'} does not exist. Did you mean building?"


def test_a_directory_without_a_simulation_config_points_to_its_parent_simulation(tmp_path: Path) -> None:
    executable = write_building_simulation(directory=tmp_path / "building") / "Executable"
    executable.mkdir()

    reason = simulation_of(simulation=executable).reason_it_is_not_a_simulation(command_name="run", working_directory=executable)

    assert reason is not None
    not_a_simulation = f"Executable is not a simulation folder. It has no server{os.sep}simulation.json."
    assert reason.startswith(f"{not_a_simulation} The simulation is the folder above it. Run '")
    assert reason.endswith("ecosim run ..'.")


def test_a_simulation_given_as_the_directory_above_is_named_after_that_directory(tmp_path: Path) -> None:
    executable = write_building_simulation(directory=tmp_path / "building") / "Executable"
    executable.mkdir()

    assert simulation_of(simulation=executable / "..").name == "building"


def test_a_directory_with_simulations_lists_them(tmp_path: Path) -> None:
    for name in ("building", "building_hpc"):
        write_building_simulation(directory=tmp_path / name)

    reason = simulation_of(simulation=tmp_path).reason_it_is_not_a_simulation(command_name="check", working_directory=tmp_path)

    assert reason is not None
    assert "It contains the simulations building and building_hpc. Run for example " in reason
    assert reason.endswith("ecosim check building'.")


def test_a_simulation_config_given_as_the_simulation_is_rejected_as_a_file(tmp_path: Path) -> None:
    simulation_config = write_building_simulation(directory=tmp_path) / "server" / "simulation.json"

    assert simulation_of(simulation=simulation_config).reason_it_is_not_a_simulation(command_name="check") == (
        f"{simulation_config} is a file, not a simulation folder. "
        + "Pass the folder with server/ and Modules/, or pass the file with --simulation-config."
    )


def test_a_missing_simulation_config_given_by_option_is_reported(tmp_path: Path) -> None:
    write_building_simulation(directory=tmp_path)

    reason = simulation_of(simulation=tmp_path, simulation_config=tmp_path / "simulaton.json").reason_it_is_not_a_simulation(command_name="check")

    assert reason == f"the simulation config {tmp_path / 'simulaton.json'} does not exist"
