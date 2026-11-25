#!/usr/bin/env python3
"""Build the source distribution and the wheel of the given subprojects, or of every subproject except
integration-tests, into `dist`.

Usage: cd dev && python -m release.build_release_packages [ecosim-common ecosim-server ...]
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
        run([get_uv_path(), "build", "--no-sources", "--out-dir", str(PACKAGE_DIRECTORY)], cwd=project)
    except subprocess.CalledProcessError as error:
        error_print(f"Building {project.name} failed with exit code {error.returncode}.")
        return False
    return True


def selected_projects(names: list[str]) -> list[Path]:
    unknown_projects = set(names) - {project.name for project, _ in SUBPROJECTS}
    if unknown_projects:
        raise ValueError(f"unknown subprojects: {', '.join(sorted(unknown_projects))}")
    return [project for project, _ in SUBPROJECTS if project.name in names or (not names and project.name not in EXCLUDED_PROJECTS)]


def build_all_packages(projects: list[Path]) -> bool:
    shutil.rmtree(PACKAGE_DIRECTORY, ignore_errors=True)
    PACKAGE_DIRECTORY.mkdir(parents=True)
    built = [build_package(project=project) for project in projects]
    return all(built)


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Empty `dist` and build the sdist and the wheel of the given subprojects into it.")
    parser.add_argument("projects", nargs="*", help="the subprojects to build; without one, every subproject except integration-tests")
    names = parser.parse_args(arguments).projects
    try:
        projects = selected_projects(names=names)
    except ValueError as error:
        error_print(error)
        return 1
    return 0 if build_all_packages(projects=projects) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
