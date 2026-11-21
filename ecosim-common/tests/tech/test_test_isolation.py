import signal
import sys

import pytest

pytest_plugins = ["pytester"]


@pytest.mark.parametrize(
    ("signal_number", "exit_status"),
    [
        (signal.SIGINT, pytest.ExitCode.INTERRUPTED),
        # on Windows os.kill ends the process with the signal number as its exit code
        (signal.SIGTERM, signal.SIGTERM if sys.platform == "win32" else -signal.SIGTERM),
    ],
)
def test_signal_stops_the_test_run(pytester: pytest.Pytester, signal_number: signal.Signals, exit_status: int) -> None:
    """The first inner test makes the signal hit the handlers left by 'reset_instance', not the ones Python starts with."""
    pytester.makepyfile(
        f"""
        import os


        def test_whose_teardown_resets_the_signal_handlers():
            pass


        def test_receiving_the_signal():
            os.kill(os.getpid(), {int(signal_number)})
        """,
    )

    result = pytester.runpytest_subprocess(timeout=60)

    assert result.ret == exit_status
