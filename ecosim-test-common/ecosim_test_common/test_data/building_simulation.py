import shutil
from pathlib import Path

from ecosim_test_common.resources.resource_utils import resource_path_file

BUILDING_MODULES = resource_path_file("hpc/modules")


def write_building_simulation(folder: Path) -> Path:
    """Copies the building example in the layout of a simulation folder: server/ with the two server files and Modules/ with the simulators."""
    for simulator in ("house", "occupancy", "weather"):
        shutil.copytree(src=BUILDING_MODULES / simulator, dst=folder / "Modules" / simulator)
    (folder / "server").mkdir(parents=True)
    for file_name in ("simulation.json", "preferences.ini"):
        shutil.copy(src=BUILDING_MODULES / file_name, dst=folder / "server" / file_name)
    return folder
