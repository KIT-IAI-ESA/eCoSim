#!/usr/bin/env python3
"""Creates new expected performance data: runs the performance tests repeatedly and writes the mean of each time."""

import argparse
import subprocess
import sys
from datetime import datetime
from typing import List, Sequence

from config import get_uv_path, subproject_environment
from run_performance_tests import INTEGRATION_TESTS, performance_pytest_command

DEFAULT_REPETITIONS = 10
# the same format as FILE_NAME_DATE_TIME_FORMAT in integration_tests/server_client/performance/tooling/performance_setup.py
FILE_NAME_DATE_TIME_FORMAT = "%Y-%m-%d_%H%M%S"
AGGREGATION_MODULE = "integration_tests.server_client.performance.tooling.main_create_test_data"

DESCRIPTION = """Runs the performance tests repeatedly, each run in its own pytest process like a normal run.
Afterwards, the mean of each time of all runs is written per protocol as new expected data to
integration-tests/integration_tests/resources/performance/DATE_TIME_PROTOCOL_MACHINE.jsonl.

Set ECOSIM_PERFORMANCE_MACHINE to choose the machine name of the data."""


def now() -> datetime:
    return datetime.now()


def run(command: List[str]) -> int:
    print(f"==> {INTEGRATION_TESTS.name}: {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=str(INTEGRATION_TESTS), env=subproject_environment()).returncode


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description=DESCRIPTION, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repetitions", type=int, default=DEFAULT_REPETITIONS, help=f"number of test runs (default {DEFAULT_REPETITIONS})")
    arguments, pytest_arguments = parser.parse_known_args(argv)
    # the result files have a precision of seconds, so the start is truncated to include the first run
    since = now().strftime(FILE_NAME_DATE_TIME_FORMAT)
    for repetition in range(1, arguments.repetitions + 1):
        print(f"==> performance test run {repetition}/{arguments.repetitions}", flush=True)
        run(performance_pytest_command(pytest_arguments))
    return run([get_uv_path(), "run", "python", "-m", AGGREGATION_MODULE, "--since", since])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
