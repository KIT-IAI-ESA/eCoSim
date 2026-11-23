import subprocess
import sys
import textwrap
import time
from dataclasses import dataclass
from pathlib import Path

from ecosim.run.run_process import ProcessToStart
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS


@dataclass(frozen=True)
class FakeRunProcess:
    exit_code: int = 0
    # None runs until a signal ends it
    run_time_in_seconds: float | None = None
    ignores_the_stop: bool = False
    # a process on Windows ends every stop with the terminate exit code
    exit_code_of_a_stop: int | None = None
    stop_time_in_seconds: float = 0
    # printed before it ends on its own, like a log line of the server
    last_line: str = ""

    def to_start(self, name: str, directory: Path) -> ProcessToStart:
        return ProcessToStart(name=name, command=[sys.executable, "-c", self._script()], log_file=directory / f"{name}.log")

    @staticmethod
    def wait_until_ready(log_files: list[Path]) -> None:
        deadline = time.monotonic() + WAIT_TIMEOUT_IN_SECONDS
        while not all(log_file.is_file() and "ready" in log_file.read_text(encoding="utf-8").splitlines() for log_file in log_files):
            if time.monotonic() > deadline:
                raise TimeoutError(f"not every process printed ready in {WAIT_TIMEOUT_IN_SECONDS} s")
            time.sleep(0.05)

    def _script(self) -> str:
        return textwrap.dedent(
            f"""
            import signal, sys, time
            from ecosim_common.tech.shutdown_manager import ShutdownManager
            def stop(signal_number, frame):
                sys.exit({self.exit_code_of_a_stop})
            if {self.ignores_the_stop}:
                signal.signal(signal.SIGINT, signal.SIG_IGN)
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
            elif {self.exit_code_of_a_stop is not None}:
                signal.signal(signal.SIGINT, stop)
                signal.signal(signal.SIGTERM, stop)
            else:
                ShutdownManager().init()
            print("ready", flush=True)
            try:
                time.sleep({self.run_time_in_seconds if self.run_time_in_seconds is not None else 3600})
            except SystemExit:
                time.sleep({self.stop_time_in_seconds})
                raise
            print({self.last_line!r}, flush=True)
            sys.exit({self.exit_code})
            """,
        )


def local_run_in_a_subprocess(server: ProcessToStart, directory: Path) -> subprocess.Popen[bytes]:
    """Runs LocalRun.execute in its own process for a test with a real signal."""
    script = textwrap.dedent(
        """
        import os, sys
        from pathlib import Path
        from ecosim.run.local_run import LocalRun
        from ecosim.run.run_process import ProcessToStart
        server = ProcessToStart(name=sys.argv[2], command=sys.argv[4:], log_file=Path(sys.argv[3]))
        sys.exit(LocalRun(server=server, clients=[]).execute(working_directory=Path(sys.argv[1]), environment=dict(os.environ)).exit_code)
        """,
    )
    arguments = [str(directory), server.name, str(server.log_file), *server.command]
    return subprocess.Popen([sys.executable, "-c", script, *arguments], stdout=subprocess.DEVNULL)
