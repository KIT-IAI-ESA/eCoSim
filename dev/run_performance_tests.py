#!/usr/bin/env python3
"""Runs only the performance tests of the integration tests."""

import subprocess
import sys
from typing import List, Sequence

from config import REPO_ROOT, get_uv_path, subproject_environment

INTEGRATION_TESTS = REPO_ROOT / "integration-tests"
PERFORMANCE_TESTS = "integration_tests/server_client/performance"
# the unit tests of the performance tooling are no performance tests
PERFORMANCE_TOOLING = f"{PERFORMANCE_TESTS}/tooling"

USAGE = """Usage: python dev/run_performance_tests.py [pytest argument ...]

Runs the performance tests in integration-tests/integration_tests/server_client/performance,
without the unit tests of its 'tooling' and without the coverage report.

  python dev/run_performance_tests.py                 all performance tests
  python dev/run_performance_tests.py -k batch_steps  forward arguments to pytest

The results are written to integration-tests/integration_tests/resources/performance/actual;
set ECOSIM_PERFORMANCE_MACHINE to choose the machine name of the results."""


def pytest_command(pytest_arguments: Sequence[str]) -> List[str]:
    # '-rs' lists the skip reasons: a local machine without current results skips the comparison
    return [get_uv_path(), "run", "pytest", PERFORMANCE_TESTS, f"--ignore={PERFORMANCE_TOOLING}", "--no-cov", "-rs", *pytest_arguments]


def main(argv: Sequence[str]) -> int:
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    command = pytest_command(argv)
    print(f"==> {INTEGRATION_TESTS.name}: {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=str(INTEGRATION_TESTS), env=subproject_environment()).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
