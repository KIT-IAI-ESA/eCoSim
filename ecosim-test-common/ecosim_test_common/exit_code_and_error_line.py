from typing import Callable

import pytest


def exit_code_and_error_line(command: Callable[[], object], capsys: pytest.CaptureFixture[str]) -> tuple[object, str]:
    """Runs a command and returns its exit code and its last line on stderr."""
    try:
        exit_code = command()
    except SystemExit as system_exit:
        exit_code = system_exit.code
    error_lines = capsys.readouterr().err.splitlines()
    return exit_code, error_lines[-1] if error_lines else ""
