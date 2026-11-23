import json
from pathlib import Path
from typing import Any

import pytest
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common_fmpy.config.validate_fmu_file_or_error import validate_fmu_file_or_error
from ecosim_test_common.test_data.building_simulation import BUILDING_MODULES, BUILDING_SIMULATORS, building_fmu_files

from tests.new.written_simulation import WrittenSimulation


@pytest.fixture(scope="module")
def building_simulation(tmp_path_factory: pytest.TempPathFactory) -> WrittenSimulation:
    return WrittenSimulation.of_fmu_files(directory=tmp_path_factory.mktemp("new") / "building", fmu_files=building_fmu_files())


def _connections_of(simulation_config_file: Path) -> dict[tuple[str, str], tuple[str, str]]:
    simulators: list[dict[str, Any]] = json.loads(simulation_config_file.read_text(encoding="utf-8"))["simulators"]
    return {
        (simulator["name"], interface["name"]): (simulators[int(target["simulator"])]["name"], target["interface"])
        for simulator in simulators
        for interface in simulator["interfaces"]
        for target in interface.get("connected_to") or []
    }


def _names_in_fmc_file(fmc_file: Path, key: str) -> set[str]:
    return {interface["name"] for interface in json.loads(fmc_file.read_text(encoding="utf-8")).get(key, [])}


def test_the_building_simulation_connects_the_inputs_like_the_hand_written_one(building_simulation: WrittenSimulation) -> None:
    connections = _connections_of(simulation_config_file=building_simulation.directory / "server" / "simulation.json")

    assert len(connections) == 18
    assert connections == _connections_of(simulation_config_file=BUILDING_MODULES / "simulation.json")


@pytest.mark.parametrize("simulator", BUILDING_SIMULATORS)
@pytest.mark.parametrize("key", ["inputs", "outputs"])
def test_the_building_simulation_lists_every_interface_of_the_hand_written_fmc_files(
    building_simulation: WrittenSimulation,
    simulator: str,
    key: str,
) -> None:
    hand_written = _names_in_fmc_file(fmc_file=BUILDING_MODULES / simulator / f"{simulator}.fmc", key=key)

    assert hand_written <= _names_in_fmc_file(fmc_file=building_simulation.directory / "modules" / simulator / f"{simulator}.fmc", key=key)


@pytest.mark.parametrize("simulator", BUILDING_SIMULATORS)
def test_the_building_simulation_passes_the_fmu_validation_of_the_client(building_simulation: WrittenSimulation, simulator: str) -> None:
    validate_fmu_file_or_error(config=ConfigParser(building_simulation.directory / "modules" / simulator / "preferences.ini"), fmi_major_version=2)


def test_the_check_at_the_end_finds_no_problem_in_the_building_simulation(building_simulation: WrittenSimulation) -> None:
    assert building_simulation.report_lines[0] == "Wrote building: 3 simulators, 18 connections, no problems."
