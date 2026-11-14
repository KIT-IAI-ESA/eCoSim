"""The program of each part, with this Python when it can, so its packages reach the models."""

import importlib.util
import shutil
import sys
from pathlib import Path
from typing import assert_never

from ecosim_common.client.config.client_type import ClientType


def server_program() -> list[str]:
    return [sys.executable, "-m", "ecosim_server.main"]


def client_program(client_type: ClientType, simulator_folder: Path, search_path: str | None = None) -> list[str]:
    """Raises FileNotFoundError, with how to install it, for a client that is not installed."""
    package, script = _package_and_script_of(client_type=client_type)
    if importlib.util.find_spec(package) is not None:
        return [sys.executable, "-m", f"{package}.main"]
    # the MATLAB client needs Python 3.12, so it often has an environment of its own on the PATH
    found = shutil.which(script, path=search_path)
    if found is None:
        raise FileNotFoundError(_how_to_install(client_type=client_type, script=script, simulator_folder=simulator_folder))
    return [found]


def _package_and_script_of(client_type: ClientType) -> tuple[str, str]:
    match client_type:
        case ClientType.FMU_2:
            return "ecosim_client_fmu_v2", "ecosim-client-fmu-v2"
        case ClientType.FMU_3:
            return "ecosim_client_fmu_v3", "ecosim-client-fmu-v3"
        case ClientType.Matlab:
            return "ecosim_client_matlab", "ecosim-client-matlab"
        case ClientType.Pyro5:
            return "ecosim_client_pyro5", "ecosim-client-pyro5"
        case ClientType.Python:
            return "ecosim_client_python", "ecosim-client-python"
        case _:
            assert_never(client_type)


def _how_to_install(client_type: ClientType, script: str, simulator_folder: Path) -> str:
    match client_type:
        case ClientType.Matlab:
            return (
                f"{simulator_folder} is a MATLAB model, but {script} is not installed. Install the MATLAB client in a Python 3.12 "
                + "environment and put that environment on the PATH, see the MATLAB client guide."
            )
        case ClientType.Pyro5:
            return f"{simulator_folder} is a Pyro5 model, but {script} is not installed. Install ecosim with its extra pyro5, like ecosim[pyro5]."
        case _:
            return f"{simulator_folder} needs {script}, which is not installed here."
