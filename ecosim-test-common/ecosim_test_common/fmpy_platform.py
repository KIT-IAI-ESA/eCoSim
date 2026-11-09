from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from zipfile import ZipFile

import fmpy
import pytest


@dataclass(frozen=True)
class FMPyPlatform:
    """The platform names fmpy uses to pick the binary of an FMU, by default those of this machine."""

    # FMI 2 names its folders after the operating system and bitness of x86 processors; fmpy uses them on arm64, too
    FMI2_PLATFORM_TUPLES: ClassVar[dict[str, str]] = {
        "win32": "x86-windows",
        "win64": "x86_64-windows",
        "linux32": "x86-linux",
        "linux64": "x86_64-linux",
        "darwin32": "x86-darwin",
        "darwin64": "x86_64-darwin",
    }

    platform: str = fmpy.platform
    platform_tuple: str = fmpy.platform_tuple
    shared_library_extension: str = fmpy.sharedLibraryExtension

    def loads_binary_of(self, fmu_file: Path) -> bool:
        model_description = fmpy.read_model_description(str(fmu_file), validate=False)
        if model_description.fmiVersion.startswith("3."):
            folder = self.platform_tuple
        elif self.FMI2_PLATFORM_TUPLES.get(self.platform) == self.platform_tuple:
            folder = self.platform
        else:
            return False
        with ZipFile(fmu_file) as fmu:
            return f"binaries/{folder}/{model_description.coSimulation.modelIdentifier}{self.shared_library_extension}" in fmu.namelist()


def skip_unless_fmpy_loads(*fmu_files: Path) -> pytest.MarkDecorator:
    platform = FMPyPlatform()
    unloadable = [fmu_file.name for fmu_file in fmu_files if not platform.loads_binary_of(fmu_file)]
    return pytest.mark.skipif(bool(unloadable), reason=f"fmpy loads no binary of {', '.join(unloadable)} on {platform.platform_tuple}")
