import dataclasses
from datetime import UTC, datetime
from pathlib import Path

import pytest
from ecosim.new.simulation_file import SimulationFile
from ecosim.new.new_simulation_files import NewSimulationFiles
from ecosim.new.simulation_length import SimulationLength
from ecosim.new.simulation_model import SimulationModel
from ecosim.new.wiring import Wiring
from ecosim.simulation_folder import SimulationFolder
from ecosim_common.config.database_type import DatabaseType
from ecosim_test_common.resources.resource_utils import fmu2_model_path

from tests.new.simulation_models import create_model


def _write(simulation: Path, models: list[SimulationModel]) -> None:
    length = SimulationLength(step_size_in_milliseconds=900_000, steps=96, start_date=datetime(2024, 1, 1, tzinfo=UTC), defaults=())
    NewSimulationFiles(port=1234, database_type=DatabaseType.FILE, database_directory="results").write(
        simulation=SimulationFolder.of_path(path=simulation),
        models=models,
        simulation_file=SimulationFile(models=models, wiring=Wiring.of_models(models=models), length=length),
    )


def _model_of_fmu(fmu_file: Path) -> SimulationModel:
    model = create_model(name="feedthrough", outputs=["Float64_continuous_output"])
    return dataclasses.replace(model, interfaces=dataclasses.replace(model.interfaces, fmu_file=fmu_file))


def test_a_simulation_that_fails_while_it_is_written_leaves_no_draft_behind(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        _write(simulation=tmp_path / "simulation", models=[_model_of_fmu(fmu_file=tmp_path / "missing.fmu")])

    assert list(tmp_path.iterdir()) == []


def test_an_empty_simulation_folder_gets_the_files_and_stays_the_same_folder(tmp_path: Path) -> None:
    simulation = tmp_path / "simulation"
    simulation.mkdir()
    # a shell whose current folder is the simulation keeps it
    folder_id = simulation.stat().st_ino

    _write(simulation=simulation, models=[_model_of_fmu(fmu_file=fmu2_model_path())])

    assert simulation.stat().st_ino == folder_id
    assert sorted(path.relative_to(simulation).as_posix() for path in simulation.rglob("*") if path.is_file()) == [
        "Modules/feedthrough/feedthrough.fmc",
        "Modules/feedthrough/feedthrough.fmu",
        "Modules/feedthrough/preferences.ini",
        "server/preferences.ini",
        "server/simulation.json",
    ]
    assert [path.name for path in tmp_path.iterdir()] == ["simulation"]


def test_an_empty_simulation_folder_gets_the_files_also_when_the_folder_around_it_cannot_be_written(tmp_path: Path) -> None:
    simulation = tmp_path / "simulation"
    simulation.mkdir()
    # like a work folder of a container that sits in a folder of root
    tmp_path.chmod(0o555)
    try:
        _write(simulation=simulation, models=[_model_of_fmu(fmu_file=fmu2_model_path())])
    finally:
        tmp_path.chmod(0o755)

    assert sorted(path.name for path in simulation.iterdir()) == ["Modules", "server"]
