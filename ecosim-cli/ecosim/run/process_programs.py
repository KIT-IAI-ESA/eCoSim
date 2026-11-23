import importlib.util
import shutil
import sys
from pathlib import Path
from typing import assert_never

from ecosim_common.client.config.client_type import ClientType


def server_program() -> list[str]:
    return [sys.executable, "-m", "ecosim_server.main"]


def client_program(client_type: ClientType, simulator_directory_path: Path, search_path: str | None = None) -> list[str]:
    package, script = _package_and_script_of(client_type=client_type)
    if importlib.util.find_spec(package) is not None:
        return [sys.executable, "-m", f"{package}.main"]
    # the MATLAB client needs Python 3.12 and often has its own environment
    found = shutil.which(script, path=search_path)
    if found is None:
        raise FileNotFoundError(_how_to_install(client_type=client_type, script=script, simulator_directory_path=simulator_directory_path))
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


def _how_to_install(client_type: ClientType, script: str, simulator_directory_path: Path) -> str:
    match client_type:
        case ClientType.Matlab:
            return (
                f"{simulator_directory_path} is a MATLAB model, but {script} is not installed. Install the MATLAB client in a Python 3.12 "
                + "environment and put that environment on the PATH. See the MATLAB client guide."
            )
        case ClientType.Pyro5:
            return f"{simulator_directory_path} is a Pyro5 model, but {script} is not installed. Install ecosim-cli[pyro5]."
        case _:
            return f"{simulator_directory_path} needs {script}. It is not installed."
