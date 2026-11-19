#!/usr/bin/env python3
"""Build the source distribution and the wheel of every subproject except integration-tests into `dist`.

Usage: python dev/build_packages.py
"""

import argparse
import shutil
import subprocess
from pathlib import Path

import sys

from config import REPO_ROOT, SUBPROJECTS, error_print, get_uv_path, run

PACKAGE_DIRECTORY = REPO_ROOT / "dist"
EXCLUDED_PROJECTS = frozenset({"integration-tests"})


def build_package(project: Path) -> bool:
    print(f"\n==> Building {project.name}")
    try:
        run([get_uv_path(), "build", "--out-dir", str(PACKAGE_DIRECTORY)], cwd=project)
    except subprocess.CalledProcessError as error:
        error_print(f"Building {project.name} failed with exit code {error.returncode}.")
        return False
    return True


def build_all_packages() -> bool:
    shutil.rmtree(PACKAGE_DIRECTORY, ignore_errors=True)
    PACKAGE_DIRECTORY.mkdir(parents=True)
    built = [build_package(project=project) for project, _ in SUBPROJECTS if project.name not in EXCLUDED_PROJECTS]
    return all(built)


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Empty `dist` and build the source distribution and the wheel of every subproject except integration-tests into it.",
    )
    parser.parse_args(arguments)
    return 0 if build_all_packages() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
