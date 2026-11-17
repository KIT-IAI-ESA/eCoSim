from pathlib import Path

import fmpy


def binary_platforms(fmu_file: Path) -> list[str]:
    # fmpy lists the C sources of an FMU as the platform c-code
    return [platform for platform in fmpy.supported_platforms(filename=str(fmu_file)) if platform != "c-code"]
