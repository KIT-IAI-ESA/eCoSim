import pytest
from ecosim.main import run_command
from ecosim_test_common.exit_code_and_error_line import exit_code_and_error_line


def error_of(arguments: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[object, str]:
    """Runs an ecosim command and returns its exit code and its last line on stderr."""
    return exit_code_and_error_line(command=lambda: run_command(arguments=arguments), capsys=capsys)
