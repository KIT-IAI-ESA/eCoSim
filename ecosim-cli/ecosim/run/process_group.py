import os
import signal
import subprocess
import sys


def process_group_flags() -> int:
    # in its own process group a process gets no Ctrl-C from the terminal
    if sys.platform == "win32":
        return subprocess.CREATE_NEW_PROCESS_GROUP
    return 0


def new_process_group() -> int | None:
    # Windows has no POSIX process groups
    return None if sys.platform == "win32" else 0


def request_stop(process: subprocess.Popen[bytes], interrupted: bool) -> None:
    if sys.platform == "win32":
        # arrives as SIGBREAK
        os.kill(process.pid, signal.CTRL_BREAK_EVENT)
        return
    _signal_group(process=process, signal_number=signal.SIGINT if interrupted else signal.SIGTERM)


def kill_process_group(process: subprocess.Popen[bytes]) -> None:
    if sys.platform == "win32":
        # the Python of a virtual environment starts the real one as its child
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
        return
    # the group includes a MATLAB process that the engine started
    _signal_group(process=process, signal_number=signal.SIGKILL)


def _signal_group(process: subprocess.Popen[bytes], signal_number: int) -> None:
    try:
        os.killpg(process.pid, signal_number)
    except ProcessLookupError:
        pass
