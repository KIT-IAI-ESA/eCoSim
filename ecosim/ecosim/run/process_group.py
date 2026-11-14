"""A process group for each part, so a Ctrl-C reaches only ecosim run, which stops the parts in order."""

import os
import signal
import subprocess
import sys


def process_group_flags() -> int:
    if sys.platform == "win32":
        return subprocess.CREATE_NEW_PROCESS_GROUP
    return 0


def new_process_group() -> int | None:
    # Windows has no process groups of this kind, see process_group_flags
    return None if sys.platform == "win32" else 0


def request_stop(process: subprocess.Popen[bytes], interrupted: bool) -> None:
    """A Ctrl-C ends the parts with the interrupt exit code, any other stop with the terminate exit code."""
    if sys.platform == "win32":
        # arrives as SIGBREAK, which ShutdownManager treats as a terminate signal
        os.kill(process.pid, signal.CTRL_BREAK_EVENT)
        return
    _signal_group(process=process, signal_number=signal.SIGINT if interrupted else signal.SIGTERM)


def kill_process_group(process: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        # the whole tree, since the Python of a virtual environment starts the real one as its child
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
        return
    # the whole group, which ends a MATLAB process that the engine started as well
    _signal_group(process=process, signal_number=signal.SIGKILL)


def _signal_group(process: subprocess.Popen[bytes], signal_number: int) -> None:
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        # the part has ended in the meantime
        pass
