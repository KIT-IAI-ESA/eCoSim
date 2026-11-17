from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum

from ecosim_common.tech.datetime.readable_duration import readable_duration
from ecosim_common.tech.shutdown_manager import SIGNAL_GRACE_IN_SECONDS, ShutdownManager
from ecosim_server.failure_texts import LOST_CLIENTS_PREFIX, LOST_CLIENTS_SUFFIX, RUN_FAILED_PREFIX

from ecosim.report_lines import shown_path, with_shown_paths
from ecosim.run.log_line import LogLine
from ecosim.run.reason_lines import reason_lines
from ecosim.run.run_process import RunProcess
from ecosim.run.server_log_follower import ServerLogFollower, line_to_show


class RunEnd(Enum):
    FINISHED = "finished"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    TERMINATED = "terminated"


@dataclass
class RunWatch:
    """Stops every process when one fails or a stop signal arrives."""

    server: RunProcess
    clients: list[RunProcess]
    follower: ServerLogFollower
    stop_timeout_in_seconds: float
    client_end_timeout_in_seconds: float
    started_at: float
    end: RunEnd | None = None
    _failed_process: RunProcess | None = None
    _first_signal_at: float | None = None
    _server_ended_at: float | None = None
    _ended: list[RunProcess] = field(default_factory=list)
    _killed: list[RunProcess] = field(default_factory=list)
    _lost_simulator_names: list[str] = field(default_factory=list)
    _server_stops_the_run: bool = False

    def processes(self) -> list[RunProcess]:
        return [self.server, *self.clients]

    def is_running(self) -> bool:
        return any(process.is_running() for process in self.processes())

    def on_stop_signal(self, interrupted: bool, received_at: float) -> None:
        if self._first_signal_at is None:
            self._first_signal_at = received_at
            self.end = self.end or (RunEnd.INTERRUPTED if interrupted else RunEnd.TERMINATED)
            print("Stopping the run. Press Ctrl-C again to kill it." if interrupted else "Stopping the run.", flush=True)
            self._stop(processes=self.processes(), interrupted=interrupted)
        elif received_at - self._first_signal_at > SIGNAL_GRACE_IN_SECONDS:
            # 'uv run' sends one Ctrl-C twice
            self.kill()

    def kill(self) -> None:
        for process in self.processes():
            process.kill()

    def handle_changes(self) -> None:
        ended = [process for process in self.processes() if not process.is_running() and process not in self._ended]
        self._ended += ended
        # shows the server lines about a failed client before a stop begins
        for log_line in self.follower.new_log_lines():
            self._on_server_log_line(log_line=log_line)
        for process in self._the_first_failure_first(ended=ended):
            self._on_end(process=process)
        if self._server_ended_at is not None and time.monotonic() - self._server_ended_at > self.client_end_timeout_in_seconds:
            self._stop(processes=self.clients, interrupted=False)
        self._kill_the_overdue()

    def exit_code(self) -> int:
        match self.end:
            case RunEnd.INTERRUPTED:
                return ShutdownManager.INTERRUPT_EXIT_CODE
            case RunEnd.TERMINATED:
                return ShutdownManager.TERMINATE_EXIT_CODE
            case RunEnd.FAILED if self._failed_process is not self.server:
                # the server ends with this code itself when it loses a client
                return ShutdownManager.FAILED_RUN_EXIT_CODE
        code = self.server.exit_code()
        # the code of a shell for a process that a signal ended
        return code if code >= 0 else 128 - code

    def _on_server_log_line(self, log_line: LogLine) -> None:
        # like 'Lost client house#house, weather#weather while waiting for ...'
        lost_clients_pattern = f"{re.escape(LOST_CLIENTS_PREFIX)}(?P<client_ids>.+?){re.escape(LOST_CLIENTS_SUFFIX)}"
        lost_clients = re.search(pattern=lost_clients_pattern, string=log_line.message)
        if lost_clients is not None:
            self._lost_simulator_names += [client_id.split("#")[-1] for client_id in lost_clients["client_ids"].split(", ")]
        line = line_to_show(log_line=log_line, shows_warnings=self.end is None and not self._server_stops_the_run)
        if line is not None:
            print(line, flush=True)
        self._server_stops_the_run = self._server_stops_the_run or log_line.message.startswith(RUN_FAILED_PREFIX)

    def _the_first_failure_first(self, ended: list[RunProcess]) -> list[RunProcess]:
        # the other processes only lost their connection
        failed = [process for process in ended if process.exit_code() != 0]
        lost = [process for process in failed if process.name in self._lost_simulator_names]
        first = (lost or [process for process in failed if process is self.server] or failed)[:1]
        return [*first, *(process for process in ended if process not in first)]

    def _on_end(self, process: RunProcess) -> None:
        if process is self.server:
            self._server_ended_at = time.monotonic()
        if process.exit_code() == 0:
            if process is self.server and self.end is None:
                self.end = RunEnd.FINISHED
            return
        if self.end is None:
            self._fail(process=process)
        elif self.end is RunEnd.FINISHED and process.stop_requested_at is None:
            print(f"{process.end_text()} after the run had finished. See {shown_path(path=process.log_file)}.", flush=True)

    def _fail(self, process: RunProcess) -> None:
        self.end, self._failed_process = RunEnd.FAILED, process
        print(f"{process.end_text()}. The end of {shown_path(path=process.log_file)}:", flush=True)
        for line in reason_lines(log_file=process.log_file, start=process.log_start):
            print(f"    {with_shown_paths(text=line)}", flush=True)
        print("Stopping the clients." if process is self.server else "Stopping the server and the other clients.", flush=True)
        self._stop(processes=self.processes(), interrupted=False)

    def _kill_the_overdue(self) -> None:
        for process in self.processes():
            if process.is_overdue(stop_timeout_in_seconds=self.stop_timeout_in_seconds) and process not in self._killed:
                process.kill()
                self._killed.append(process)
                print(f"{process.name} did not stop within {readable_duration(seconds=self.stop_timeout_in_seconds)}. It was killed.", flush=True)

    @staticmethod
    def _stop(processes: list[RunProcess], interrupted: bool) -> None:
        for process in processes:
            process.request_stop(interrupted=interrupted)
