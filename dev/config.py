import os
import shutil
import subprocess

import sys
from pathlib import Path
from typing import List

# The repository root is the parent directory of the directory where this script resides
REPO_ROOT = Path(__file__).resolve().parent.parent

SUBPROJECTS: List[tuple[Path, List[str]]] = [
    (REPO_ROOT / "ecosim-common", ["dev"]),
    (REPO_ROOT / "ecosim-server", ["dev"]),
    (REPO_ROOT / "integration-tests", []),
    (REPO_ROOT / "ecosim-client-fmu-v2", ["dev"]),
    (REPO_ROOT / "ecosim-client-fmu-v3", ["dev"]),
]


def error_print(*args: object) -> None:
    print(*args, file=sys.stderr)


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
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


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
        "uv executable not found. Please ensure uv is installed and either:\n"
        "1. Available in PATH, or\n"
        "2. Installed in a standard location",
    )
