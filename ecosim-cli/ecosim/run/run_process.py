from __future__ import annotations

import signal
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from ecosim.report_lines import command_text
from ecosim.run.process_group import kill_process_group, new_process_group, process_group_flags, request_stop


@dataclass(frozen=True)
class ProcessToStart:
    name: str
    command: list[str]
    log_file: Path

    def start(self, working_directory: Path, environment: dict[str, str]) -> RunProcess:
        with self.log_file.open("a", encoding="utf-8") as log:
            # a restore appends to the logs of the run
            log.write(f"== {datetime.now():%Y-%m-%d %H:%M:%S} {command_text(arguments=self.command)}\n")
            log.flush()
            log_start = log.tell()
            process = subprocess.Popen(
                self.command,
                cwd=working_directory,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=environment,
                creationflags=process_group_flags(),
                process_group=new_process_group(),
            )
        return RunProcess(name=self.name, log_file=self.log_file, log_start=log_start, process=process)


@dataclass
class RunProcess:
    name: str
    log_file: Path
    # where this run begins in the log
    log_start: int
    process: subprocess.Popen[bytes] = field(repr=False)
    stop_requested_at: float | None = None

    def is_running(self) -> bool:
        return self.process.poll() is None

    def exit_code(self) -> int:
        return int(self.process.returncode)

    def end_text(self) -> str:
        code = self.exit_code()
        if code >= 0:
            return f"{self.name} stopped with exit code {code}"
        signal_names = {number.value: number.name for number in signal.Signals}
        return f"{self.name} was killed by signal {-code} ({signal_names.get(-code, 'unknown')})"

    def request_stop(self, interrupted: bool) -> None:
        if not self.is_running() or self.stop_requested_at is not None:
            return
        self.stop_requested_at = time.monotonic()
        request_stop(process=self.process, interrupted=interrupted)

    def is_overdue(self, stop_timeout_in_seconds: float) -> bool:
        return self.is_running() and self.stop_requested_at is not None and time.monotonic() - self.stop_requested_at > stop_timeout_in_seconds

    def kill(self) -> None:
        if self.is_running():
            kill_process_group(process=self.process)
