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
class PartToStart:
    """The server or a client of a run: its command, and the log file that gets everything it prints."""

    name: str
    command: list[str]
    log_file: Path

    def start(self, working_folder: Path, environment: dict[str, str]) -> RunPart:
        with self.log_file.open("a", encoding="utf-8") as log:
            # a restore adds to the logs of the run, and each log says what ran
            log.write(f"== {datetime.now():%Y-%m-%d %H:%M:%S} {command_text(arguments=self.command)}\n")
            log.flush()
            log_start = log.tell()
            process = subprocess.Popen(
                self.command,
                cwd=working_folder,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                env=environment,
                creationflags=process_group_flags(),
                process_group=new_process_group(),
            )
        return RunPart(name=self.name, log_file=self.log_file, log_start=log_start, process=process)


@dataclass
class RunPart:
    name: str
    log_file: Path
    # where this run begins in a log that a restore adds to
    log_start: int
    process: subprocess.Popen[bytes] = field(repr=False)
    stop_requested_at: float | None = None
    has_ended: bool = False

    def is_running(self) -> bool:
        return self.process.poll() is None

    def has_just_ended(self) -> bool:
        if self.has_ended or self.is_running():
            return False
        self.has_ended = True
        return True

    def exit_code(self) -> int:
        # once the part has ended
        return int(self.process.returncode)

    def end_text(self) -> str:
        """Like 'house stopped with exit code 1' or 'house was killed by signal 9 (SIGKILL)'."""
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

    def is_overdue(self, seconds_to_stop: float) -> bool:
        return self.is_running() and self.stop_requested_at is not None and time.monotonic() - self.stop_requested_at > seconds_to_stop

    def kill(self) -> None:
        if self.is_running():
            kill_process_group(process=self.process)
