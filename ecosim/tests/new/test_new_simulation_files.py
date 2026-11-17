import dataclasses
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ecosim.new.input_connections import InputConnections
from ecosim.new.new_simulation_config import NewSimulationConfig
from ecosim.new.new_simulation_files import NewSimulationFiles
from ecosim.new.simulation_length import SimulationLength
from ecosim.new.simulation_model import SimulationModel
from ecosim.simulation_directory import SimulationDirectory
from ecosim_common.config.database_type import DatabaseType
from ecosim_test_common.resources.resource_utils import fmu2_model_path

from tests.new.simulation_models import create_model


def _write(simulation: Path, models: list[SimulationModel]) -> None:
    length = SimulationLength(step_size_in_ms=900_000, steps=96, start_date=datetime(2024, 1, 1, tzinfo=UTC), defaults=())
    NewSimulationFiles(port=1234, database_type=DatabaseType.FILE, database_directory="results").write(
        simulation=SimulationDirectory.of_path(path=simulation),
        models=models,
        new_simulation_config=NewSimulationConfig(
            models=models,
            input_connections=InputConnections.of_models(models=models, given_connections=[]),
            delayed=[],
            length=length,
        ),
    )


def _model_of_fmu(fmu_file: Path) -> SimulationModel:
    model = create_model(name="feedthrough", outputs=["Float64_continuous_output"])
    return dataclasses.replace(model, interfaces=dataclasses.replace(model.interfaces, fmu_file=fmu_file))


def test_a_simulation_that_fails_while_it_is_written_leaves_no_draft_behind(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _write(simulation=tmp_path / "simulation", models=[_model_of_fmu(fmu_file=tmp_path / "missing.fmu")])

    assert list(tmp_path.iterdir()) == []


def test_an_empty_simulation_directory_gets_the_files_and_stays_the_same_directory(tmp_path: Path) -> None:
    simulation = tmp_path / "simulation"
    simulation.mkdir()
    # a shell that is in the simulation folder stays in it
    directory_id = simulation.stat().st_ino

    _write(simulation=simulation, models=[_model_of_fmu(fmu_file=fmu2_model_path())])

    assert simulation.stat().st_ino == directory_id
    assert sorted(path.relative_to(simulation).as_posix() for path in simulation.rglob("*") if path.is_file()) == [
        "Modules/feedthrough/feedthrough.fmc",
        "Modules/feedthrough/feedthrough.fmu",
        "Modules/feedthrough/preferences.ini",
        "server/preferences.ini",
        "server/simulation.json",
    ]
    assert [path.name for path in tmp_path.iterdir()] == ["simulation"]


@pytest.mark.skipif(sys.platform == "win32" or os.geteuid() == 0, reason="chmod does not stop Windows or root from writing")
def test_an_empty_simulation_directory_is_filled_inside_a_read_only_directory(tmp_path: Path) -> None:
    simulation = tmp_path / "simulation"
    simulation.mkdir()
    tmp_path.chmod(0o555)
    try:
        _write(simulation=simulation, models=[_model_of_fmu(fmu_file=fmu2_model_path())])
    finally:
        tmp_path.chmod(0o755)

    assert sorted(path.name for path in simulation.iterdir()) == ["Modules", "server"]
