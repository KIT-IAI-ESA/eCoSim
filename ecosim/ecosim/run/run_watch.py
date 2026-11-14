from __future__ import annotations

import re
import signal
import time
from dataclasses import dataclass, field
from enum import Enum

from ecosim_common.tech.datetime.readable_duration import readable_duration
from ecosim_common.tech.shutdown_manager import SIGNAL_GRACE_IN_SECONDS, ShutdownManager

from ecosim.report_lines import shown_path, with_shown_paths
from ecosim.run.log_line import LogLine
from ecosim.run.reason_lines import reason_lines
from ecosim.run.run_part import RunPart
from ecosim.run.server_log_follower import ServerLogFollower, line_to_show

# like 'Lost client house#house, weather#weather while waiting for ...'
LOST_CLIENT_PATTERN = re.compile(r"Lost client (?P<client_ids>.+?) while ")


class RunEnd(Enum):
    FINISHED = "finished"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    TERMINATED = "terminated"


@dataclass
class RunWatch:
    """The first part that fails, or a signal, stops every part. Only the end of the server ends the run."""

    server: RunPart
    clients: list[RunPart]
    follower: ServerLogFollower
    seconds_to_stop: float
    seconds_for_the_clients_to_end: float
    end: RunEnd | None = None
    _failed_part: RunPart | None = None
    _first_signal_at: float | None = None
    _server_ended_at: float | None = None
    _killed: list[RunPart] = field(default_factory=list)
    # the simulators the server lost, which failed before the others lost their connection
    _lost_simulator_names: list[str] = field(default_factory=list)
    _server_stops_the_run: bool = False

    def parts(self) -> list[RunPart]:
        return [self.server, *self.clients]

    def is_running(self) -> bool:
        return any(part.is_running() for part in self.parts())

    def look(self, signals: list[tuple[int, float]]) -> None:
        while signals:
            self._on_signal(*signals.pop(0))
        ended = [part for part in self.parts() if part.has_just_ended()]
        # after the poll and before a stop begins, so the server lines that name a failed client are shown
        self._show(log_lines=self.follower.new_log_lines())
        for part in self._the_first_failure_first(ended=ended):
            self._on_end(part=part)
        if self._server_ended_at is not None and time.monotonic() - self._server_ended_at > self.seconds_for_the_clients_to_end:
            self._stop(parts=self.clients, interrupted=False)
        for part in [part for part in self.parts() if part.is_overdue(seconds_to_stop=self.seconds_to_stop) and part not in self._killed]:
            part.kill()
            self._killed.append(part)
            print(f"{part.name} did not stop within {readable_duration(seconds=self.seconds_to_stop)}, so it was killed.", flush=True)

    def exit_code(self) -> int:
        match self.end:
            case RunEnd.INTERRUPTED:
                return ShutdownManager.INTERRUPT_EXIT_CODE
            case RunEnd.TERMINATED:
                return ShutdownManager.TERMINATE_EXIT_CODE
            case RunEnd.FAILED if self._failed_part is not self.server:
                # the code the server ends with itself when it loses a client, ecosim run only stops it sooner
                return ShutdownManager.FAILED_RUN_EXIT_CODE
        code = self.server.exit_code()
        # the shell's code for a process that a signal ended
        return code if code >= 0 else 128 - code

    def _show(self, log_lines: list[LogLine]) -> None:
        for log_line in log_lines:
            match = LOST_CLIENT_PATTERN.search(log_line.message)
            if match is not None:
                self._lost_simulator_names += [client_id.split("#")[-1] for client_id in match["client_ids"].split(", ")]
            line = line_to_show(log_line=log_line, shows_warnings=self.end is None and not self._server_stops_the_run)
            if line is not None:
                print(line, flush=True)
            # the error with which the server begins to stop the run itself
            self._server_stops_the_run = self._server_stops_the_run or log_line.message.startswith("The run failed: ")

    def _the_first_failure_first(self, ended: list[RunPart]) -> list[RunPart]:
        """Puts first the client that the server lost, else the server, as the others only lost their connection."""
        failed = [part for part in ended if part.exit_code() != 0]
        lost = [part for part in failed if part.name in self._lost_simulator_names]
        first = (lost or [part for part in failed if part is self.server] or failed)[:1]
        return [*first, *(part for part in ended if part not in first)]

    def _on_end(self, part: RunPart) -> None:
        if part is self.server:
            self._server_ended_at = time.monotonic()
        if part.exit_code() == 0:
            # a client that ends normally changes nothing, only the server's end ends the run
            if part is self.server and self.end is None:
                self.end = RunEnd.FINISHED
            return
        if self.end is None:
            self._fail(part=part)
        elif self.end is RunEnd.FINISHED and part.stop_requested_at is None:
            print(f"{part.end_text()} after the run had finished. See {shown_path(path=part.log_file)}.", flush=True)

    def _fail(self, part: RunPart) -> None:
        self.end, self._failed_part = RunEnd.FAILED, part
        print(f"{part.end_text()}. The end of {shown_path(path=part.log_file)}:", flush=True)
        for line in reason_lines(log_file=part.log_file, start=part.log_start):
            print(f"    {with_shown_paths(text=line)}", flush=True)
        print("Stopping the clients." if part is self.server else "Stopping the server and the other clients.", flush=True)
        self._stop(parts=self.parts(), interrupted=False)

    def _on_signal(self, signal_number: int, received_at: float) -> None:
        if self._first_signal_at is None:
            self._first_signal_at = received_at
            interrupted = signal_number == signal.SIGINT
            self.end = self.end or (RunEnd.INTERRUPTED if interrupted else RunEnd.TERMINATED)
            print("Stopping the run. Press Ctrl-C again to kill it." if interrupted else "Stopping the run.", flush=True)
            self._stop(parts=self.parts(), interrupted=interrupted)
        elif received_at - self._first_signal_at > SIGNAL_GRACE_IN_SECONDS:
            # 'uv run' passes one Ctrl-C on twice, so only a later one kills
            for part in self.parts():
                part.kill()

    @staticmethod
    def _stop(parts: list[RunPart], interrupted: bool) -> None:
        for part in parts:
            part.request_stop(interrupted=interrupted)
