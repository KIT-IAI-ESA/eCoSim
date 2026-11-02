"""These hang or crash when they break, so each runs in its own process."""

import signal
import subprocess
import sys

import pytest

from ecosim_common.tech.shutdown_manager import ShutdownManager

SCRIPT_START = """
import ctypes
import os
import signal
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager

ShutdownManager().init()
"""


def _run_script(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", SCRIPT_START + script],
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_signal_does_not_deadlock_while_the_interrupted_code_holds_the_lock() -> None:
    result = _run_script(
        """
with ShutdownManager._lock:
    signal.raise_signal(signal.SIGTERM)
""",
    )

    assert result.returncode == ShutdownManager.TERMINATE_EXIT_CODE, result.stderr


def test_listener_registered_during_a_running_shutdown_is_notified() -> None:
    result = _run_script(
        """
class Late(ShutdownListener):
    def on_app_shutdown(self) -> None:
        print("late listener notified")


class Registering(ShutdownListener):
    def on_app_shutdown(self) -> None:
        ShutdownManager().register_listener(Late())


ShutdownManager().register_listener(Registering())
ShutdownManager().set_shutdown_at_application_end()
""",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.count("late listener notified") == 1


@pytest.mark.skipif(sys.platform == "win32", reason="Not supported on Windows")
@pytest.mark.parametrize(
    ("crash", "signal_number"),
    [
        ("ctypes.string_at(0)", signal.SIGSEGV),
        ("os.abort()", signal.SIGABRT),
        ("signal.raise_signal(signal.SIGFPE)", signal.SIGFPE),
    ],
)
def test_native_crash_ends_the_process_and_prints_the_python_stack(crash: str, signal_number: signal.Signals) -> None:
    result = _run_script(crash)

    assert result.returncode == -signal_number
    assert "Fatal Python error" in result.stderr
