#!/usr/bin/env python3
"""Runs the tests of every subproject except the integration tests."""

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from config import SUBPROJECTS, error_print, get_uv_path

# 'integration-tests' starts real servers on real ports and needs the other packages
# installed, so it is not part of this quick feedback run
EXCLUDED_PROJECTS = frozenset({"integration-tests", "ecosim-test-common"})

# pytest exits with 5 when it did not collect a single test. Some subprojects have no
# tests (yet), which must not fail the whole run
EXIT_CODE_NO_TESTS_COLLECTED = 5

USAGE = """Usage: python dev/run_unit_tests.py [subproject ...] [-- pytest argument ...]

Runs 'uv run pytest' in every subproject except the integration tests.

  python dev/run_unit_tests.py                        every subproject
  python dev/run_unit_tests.py ecosim-server          only the given subprojects
  python dev/run_unit_tests.py -- -k history          forward arguments to pytest

ATTENTION: no pytest arguments are passed by default."""


@dataclass(frozen=True)
class TestResult:
    project: str
    exit_code: int

    @property
    def collected_nothing(self) -> bool:
        return self.exit_code == EXIT_CODE_NO_TESTS_COLLECTED

    @property
    def failed(self) -> bool:
        return self.exit_code != 0 and not self.collected_nothing

    @property
    def summary(self) -> str:
        if self.collected_nothing:
            return "no tests"
        if self.exit_code == 0:
            return "ok"
        return f"FAILED (exit code {self.exit_code})"


def all_projects_apart_integration_tests() -> List[Path]:
    return [path for path, _ in SUBPROJECTS if path.name not in EXCLUDED_PROJECTS]


def generate_project_list_for_test(given_projects: Sequence[str]) -> List[Path]:
    if not given_projects:
        return all_projects_apart_integration_tests()
    return [path for path in all_projects_apart_integration_tests() if path.name in given_projects]


def unknown_projects(selected: Sequence[str]) -> List[str]:
    known = {path.name for path in all_projects_apart_integration_tests()}
    return [name for name in selected if name not in known]


def pytest_environment() -> Dict[str, str]:
    """'uv run' warns about and ignores an active venv of another project, so it is removed."""
    environment = os.environ.copy()
    environment.pop("VIRTUAL_ENV", None)
    return environment


def run_tests_of(
    path: Path,
    pytest_arguments: Sequence[str],
) -> TestResult:
    command = [get_uv_path(), "run", "pytest", *pytest_arguments]
    print(f"\n==> {path.name}: {' '.join(command)}", flush=True)
    completed = subprocess.run(command, cwd=str(path), env=pytest_environment())
    return TestResult(project=path.name, exit_code=completed.returncode)


def split_arguments(argv: Sequence[str]) -> Tuple[List[str], List[str]]:
    """Splits '<subproject ...> -- <pytest argument ...>' into its two parts."""
    arguments = list(argv)
    if "--" not in arguments:
        return arguments, []
    separator = arguments.index("--")
    return arguments[:separator], arguments[separator + 1 :]


def print_summary(results: Sequence[TestResult]) -> None:
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for result in results:
        print(f"  {result.project:<24}{result.summary}")
    failed = [result.project for result in results if result.failed]
    # stdout is buffered when piped, stderr is not - flush so the order stays readable
    sys.stdout.flush()
    if failed:
        error_print(f"\n{len(failed)} subproject(s) failed: {', '.join(failed)}")
    else:
        print("\nAll tests passed.")


def main(argv: Sequence[str]) -> int:
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    given_projects, pytest_arguments = split_arguments(argv)
    unknown = unknown_projects(given_projects)
    if unknown:
        error_print(f"Unknown subproject(s): {', '.join(unknown)}")
        error_print(f"Known: {', '.join(path.name for path in all_projects_apart_integration_tests())}")
        return 1
    results = [run_tests_of(path, pytest_arguments) for path in generate_project_list_for_test(given_projects)]
    print_summary(results)
    return 1 if any(result.failed for result in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
