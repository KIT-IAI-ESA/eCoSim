#!/usr/bin/env python3
"""Runs the integration tests (i.e. without the performance tests and without the unit tests)."""

import subprocess
import sys
from typing import Sequence

from config import REPO_ROOT, pytest_command, subproject_environment

INTEGRATION_TESTS = REPO_ROOT / "integration-tests"

USAGE = """Usage: python dev/run_integration_tests.py [pytest argument ...]

Runs the tests of integration-tests marked 'integration', which are all apart from the performance tests.

  python dev/run_integration_tests.py                 all integration tests
  python dev/run_integration_tests.py -k restore      forward arguments to pytest

# EXAMPLES

A single test with a specific communication protocol:

  python dev/run_integration_tests.py "integration_tests/server_client/test_client_server_batch_steps.py::test_client_server_batch_steps[tcp_socket]"
  python dev/run_integration_tests.py "integration_tests/server_client/test_client_server_batch_steps.py::test_client_server_batch_steps[dask]"
"""


def main(argv: Sequence[str]) -> int:
    if "-h" in argv or "--help" in argv:
        print(USAGE)
        return 0
    command = pytest_command(marker="integration", pytest_arguments=argv)
    print(f"==> {INTEGRATION_TESTS.name}: {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=str(INTEGRATION_TESTS), env=subproject_environment()).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
