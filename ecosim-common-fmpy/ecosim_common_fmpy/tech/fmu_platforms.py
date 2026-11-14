from pathlib import Path

import fmpy


def binary_platforms(fmu_file: Path) -> list[str]:
    """The platforms the FMU has a binary for, like linux64, to compare with fmpy.platform."""
    # fmpy lists the C sources of an FMU as the platform c-code, which no client can run
    return [platform for platform in fmpy.supported_platforms(filename=str(fmu_file)) if platform != "c-code"]
