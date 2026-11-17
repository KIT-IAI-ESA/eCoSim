import shutil
from pathlib import Path

import pytest

from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.resources.resource_utils import resource_path_file

BUILDING_MODULES = resource_path_file("hpc/modules")
BUILDING_SIMULATORS = ("house", "occupancy", "weather")


def write_building_simulation(directory: Path) -> Path:
    """Copies the building example into the layout of a simulation folder."""
    for simulator in BUILDING_SIMULATORS:
        shutil.copytree(src=BUILDING_MODULES / simulator, dst=directory / "Modules" / simulator)
    (directory / "server").mkdir(parents=True)
    for file_name in ("simulation.json", "preferences.ini"):
        shutil.copy(src=BUILDING_MODULES / file_name, dst=directory / "server" / file_name)
    return directory


def building_fmu_files() -> list[Path]:
    return [BUILDING_MODULES / name / f"{name}.fmu" for name in BUILDING_SIMULATORS]


def skip_unless_fmpy_loads_the_building_fmus() -> pytest.MarkDecorator:
    return skip_unless_fmpy_loads(*building_fmu_files())
