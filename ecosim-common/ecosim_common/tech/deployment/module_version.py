import inspect
import tomllib
from importlib.metadata import version
from pathlib import Path


def get_module_version(
    name: str,
    pyproject_file: Path | None = None,
) -> str:
    # noinspection PyBroadException
    try:
        return version(name)
    except Exception:
        pass
    file = pyproject_file or _caller_file_parent_parent_pyproject()
    # Packaging into .exe via Pyinstaller does not find the right toml to open
    try:
        with open(file, "rb") as f:
            pyproject_data = tomllib.load(f)
        return pyproject_data["project"]["version"]  # type: ignore
    except FileNotFoundError:
        return "0.0"


def _caller_file_parent_parent_pyproject() -> Path:
    # get the caller of the caller of this method (i.e. the other script that is calling 'get_module_version')
    caller_frame = inspect.currentframe().f_back.f_back  # type: ignore
    return Path(caller_frame.f_code.co_filename).parent.parent / "pyproject.toml"  # type: ignore
