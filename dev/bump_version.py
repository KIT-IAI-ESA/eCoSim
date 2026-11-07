#!/usr/bin/env python3
"""Set the eCoSim version and the pins between the eCoSim packages, then refresh each uv.lock.

Usage: python dev/bump_version.py 0.15.0
"""

import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path

from config import REPO_ROOT, SUBPROJECTS, error_print, get_uv_path, run

ECOSIM_PROJECTS = [Path("."), *(path.relative_to(REPO_ROOT) for path, _ in SUBPROJECTS)]
# the examples keep their own version but pin the eCoSim packages
ALL_PROJECTS = [*ECOSIM_PROJECTS, Path("simulation_examples")]


def read_pyproject(project: Path) -> str:
    return (project / "pyproject.toml").read_text(encoding="utf-8")


def internal_package_names(root: Path) -> list[str]:
    return [str(tomllib.loads(read_pyproject(root / project))["project"]["name"]) for project in ECOSIM_PROJECTS]


def pin_internal_packages(pyproject: str, packages: list[str], version: str) -> str:
    for package in packages:
        pyproject = re.sub(pattern=f'"{re.escape(package)}==[^"]*"', repl=f'"{package}=={version}"', string=pyproject)
    return pyproject


def set_version(root: Path, version: str) -> None:
    packages = internal_package_names(root=root)
    for project in ALL_PROJECTS:
        pyproject = pin_internal_packages(pyproject=read_pyproject(root / project), packages=packages, version=version)
        if project in ECOSIM_PROJECTS:
            pyproject = re.sub(pattern=r'^version = "[^"]*"$', repl=f'version = "{version}"', string=pyproject, count=1, flags=re.MULTILINE)
        (root / project / "pyproject.toml").write_text(pyproject, encoding="utf-8")


def refresh_lock_files(root: Path) -> None:
    for project in ALL_PROJECTS:
        run([get_uv_path(), "lock"], cwd=root / project)


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Set the version of every eCoSim package and refresh each uv.lock.")
    parser.add_argument("version", help="the new version, e.g. 0.15.0")
    version = parser.parse_args(arguments).version
    set_version(root=REPO_ROOT, version=version)
    try:
        refresh_lock_files(root=REPO_ROOT)
    except subprocess.CalledProcessError:
        error_print(f"uv lock failed, the pyproject.toml files already have version {version}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
