import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Sequence

# The repository root is the parent directory of the directory where this script resides
REPO_ROOT = Path(__file__).resolve().parent.parent

SUBPROJECTS: List[tuple[Path, List[str]]] = [
    (REPO_ROOT / "ecosim-common", ["dev"]),
    (REPO_ROOT / "ecosim-common-fmpy", ["dev"]),
    (REPO_ROOT / "ecosim-server", ["dev"]),
    (REPO_ROOT / "integration-tests", []),
    (REPO_ROOT / "ecosim-client-fmu-v2", ["dev"]),
    (REPO_ROOT / "ecosim-client-fmu-v3", ["dev"]),
    (REPO_ROOT / "ecosim-client-matlab", ["dev"]),
    (REPO_ROOT / "ecosim-hpc", ["dev"]),
    (REPO_ROOT / "ecosim-client-pyro5", ["dev"]),
    (REPO_ROOT / "ecosim-client-python", ["dev"]),
    (REPO_ROOT / "ecosim-test-common", []),
]


def error_print(*args: object) -> None:
    print(*args, file=sys.stderr)


def write_or_check(path: Path, content: str, check: bool) -> int:
    if not check:
        path.write_text(content, encoding="utf-8")
        return 0
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return 0
    error_print(f"{path.name} is out of date, run the same command without --check")
    return 1


def run(
    cmd: List[str],
    cwd: Path | None = None,
    dry_run: bool = False,
) -> None:
    as_str = " ".join(cmd)
    loc = f" (cwd={cwd})" if cwd else ""
    print(f"$ {as_str}{loc}")
    if dry_run:
        return
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True, env=subproject_environment())


def subproject_environment() -> dict[str, str]:
    """Environment without the caller's venv, so uv uses the venv of the project in cwd.

    PyCharm's uv runner sets UV_PROJECT_ENVIRONMENT to the run config's interpreter; inherited,
    it makes every `uv venv --clear` / `uv sync` target that one venv instead.
    """
    environment = os.environ.copy()
    for name in ("UV_PROJECT_ENVIRONMENT", "VIRTUAL_ENV", "VIRTUAL_ENV_PROMPT"):
        environment.pop(name, None)
    return environment


def pytest_command(
    marker: str,
    pytest_arguments: Sequence[str],
) -> List[str]:
    return [get_uv_path(), "run", "pytest", "-m", marker, *pytest_arguments]


def get_uv_path() -> str:
    """Find uv executable in a platform-independent way."""
    # First, try PATH
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path

    # Platform-specific fallback locations
    if sys.platform == "win32":
        # Windows: typically in %USERPROFILE%\.cargo\bin or %LOCALAPPDATA%\Programs\uv
        possible_paths = [
            os.path.expandvars(r"%USERPROFILE%\.cargo\bin\uv.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\uv\uv.exe"),
            os.path.expandvars(r"%APPDATA%\uv\bin\uv.exe"),
        ]
    else:
        # Unix-like (Linux/macOS)
        possible_paths = [
            os.path.expanduser("~/.cargo/bin/uv"),
            os.path.expanduser("~/.local/bin/uv"),
            "/usr/local/bin/uv",
        ]

    # Check each possible location
    for path in possible_paths:
        if os.path.isfile(path):
            return path

    raise FileNotFoundError(
        "uv executable not found. Please ensure uv is installed and either:\n1. Available in PATH, or\n2. Installed in a standard location",
    )
