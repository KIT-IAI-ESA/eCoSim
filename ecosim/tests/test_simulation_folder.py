import os
from argparse import Namespace
from pathlib import Path

import pytest
from ecosim.simulation_folder import SimulationFolder
from ecosim_test_common.test_data.building_simulation import write_building_simulation


def simulation_of(simulation: Path | None, **files: Path) -> SimulationFolder:
    options = {"simulation_config": None, "server_config": None, "simulator_dir": None, **files}
    return SimulationFolder.of_options(options=Namespace(simulation=simulation, **options))


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


def test_a_simulation_folder_with_a_simulation_config_can_be_used(tmp_path: Path) -> None:
    assert simulation_of(simulation=write_building_simulation(folder=tmp_path / "building")).reason_it_is_no_simulation(command_name="check") is None


def test_a_misspelt_simulation_folder_names_the_closest_folder(tmp_path: Path) -> None:
    write_building_simulation(folder=tmp_path / "building")

    reason = simulation_of(simulation=tmp_path / "buildng").reason_it_is_no_simulation(command_name="check")

    assert reason == f"the folder {tmp_path / 'buildng'} does not exist. Did you mean building?"


def test_a_folder_without_a_simulation_config_points_to_its_parent_simulation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = write_building_simulation(folder=tmp_path / "building") / "Executable"
    executable.mkdir()
    monkeypatch.chdir(executable)

    reason = simulation_of(simulation=None).reason_it_is_no_simulation(command_name="run")

    assert (
        reason
        == f"Executable is not a simulation folder: it has no server{os.sep}simulation.json. "
        + "The simulation is the folder above it, so run 'ecosim run ..'."
    )


def test_a_simulation_given_as_the_folder_above_is_named_after_that_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    executable = write_building_simulation(folder=tmp_path / "building") / "Executable"
    executable.mkdir()
    monkeypatch.chdir(executable)

    assert simulation_of(simulation=Path("..")).name == "building"


def test_a_folder_that_holds_simulations_names_them(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("building", "building_hpc"):
        write_building_simulation(folder=tmp_path / name)
    monkeypatch.chdir(tmp_path)

    reason = simulation_of(simulation=None).reason_it_is_no_simulation(command_name="check")

    assert reason == (
        f"{tmp_path.name} is not a simulation folder: it has no server{os.sep}simulation.json. "
        + "It holds the simulations building and building_hpc, so run for example 'ecosim check building'."
    )


def test_a_simulation_config_given_as_the_simulation_is_named_a_file(tmp_path: Path) -> None:
    simulation_config = write_building_simulation(folder=tmp_path) / "server" / "simulation.json"

    assert simulation_of(simulation=simulation_config).reason_it_is_no_simulation(command_name="check") == (
        f"{simulation_config} is a file, not a simulation folder. "
        + "Give the folder that holds server/ and Modules/, or the file with --simulation-config."
    )


def test_a_simulation_config_given_by_option_that_does_not_exist_is_named(tmp_path: Path) -> None:
    write_building_simulation(folder=tmp_path)

    reason = simulation_of(simulation=tmp_path, simulation_config=tmp_path / "simulaton.json").reason_it_is_no_simulation(command_name="check")

    assert reason == f"the simulation config {tmp_path / 'simulaton.json'} does not exist"
