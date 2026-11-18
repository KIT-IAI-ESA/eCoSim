from __future__ import annotations

import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

from ecosim.run.run_process import ProcessToStart, RunProcess
from ecosim.run.run_watch import RunEnd, RunWatch
from ecosim.run.server_log_follower import ServerLogFollower


@dataclass(frozen=True)
class RunOutcome:
    end: RunEnd
    exit_code: int
    run_time_in_seconds: float


@dataclass(frozen=True)
class LocalRun:
    server: ProcessToStart
    clients: list[ProcessToStart]
    stop_timeout_in_seconds: float = 10
    client_end_timeout_in_seconds: float = 15
    # the client the server lost can end a moment after the clients that only lost their connection
    lost_client_wait_in_seconds: float = 5
    # Windows handles Ctrl-C only between waits
    poll_interval_in_seconds: float = 0.5

    def execute(self, working_directory: Path, environment: dict[str, str]) -> RunOutcome:
        received_signals: list[tuple[int, float]] = []

        def note_signal(signal_number: int, frame: FrameType | None) -> None:
            received_signals.append((signal_number, time.monotonic()))

        previous_handlers = {signal_number: signal.signal(signal_number, note_signal) for signal_number in _stop_signals()}
        try:
            watch = self.start(working_directory=working_directory, environment=environment)
            return self.wait_for_the_end(watch=watch, received_signals=received_signals)
        finally:
            for signal_number, previous_handler in previous_handlers.items():
                signal.signal(signal_number, previous_handler)

    def start(self, working_directory: Path, environment: dict[str, str]) -> RunWatch:
        started_at = time.monotonic()
        started: list[RunProcess] = []
        try:
            for process_to_start in [self.server, *self.clients]:
                started.append(process_to_start.start(working_directory=working_directory, environment=environment))
        except BaseException:
            for process in started:
                process.kill()
            raise
        return RunWatch(
            server=started[0],
            clients=started[1:],
            follower=ServerLogFollower(log_file=started[0].log_file, read_up_to=started[0].log_start),
            stop_timeout_in_seconds=self.stop_timeout_in_seconds,
            client_end_timeout_in_seconds=self.client_end_timeout_in_seconds,
            lost_client_wait_in_seconds=self.lost_client_wait_in_seconds,
            started_at=started_at,
        )

    def wait_for_the_end(self, watch: RunWatch, received_signals: list[tuple[int, float]]) -> RunOutcome:
        try:
            while watch.is_running():
                _handle_signals_and_changes(watch=watch, received_signals=received_signals)
                time.sleep(self.poll_interval_in_seconds)
            _handle_signals_and_changes(watch=watch, received_signals=received_signals)
        except BaseException:
            watch.kill()
            raise
        return RunOutcome(end=watch.end or RunEnd.FAILED, exit_code=watch.exit_code(), run_time_in_seconds=time.monotonic() - watch.started_at)


def _handle_signals_and_changes(watch: RunWatch, received_signals: list[tuple[int, float]]) -> None:
    while received_signals:
        signal_number, received_at = received_signals.pop(0)
        watch.on_stop_signal(interrupted=signal_number == signal.SIGINT, received_at=received_at)
    watch.handle_changes()


def _stop_signals() -> list[signal.Signals]:
    if sys.platform == "win32":
        # Windows sends the stop of a process group as SIGBREAK
        return [signal.SIGINT, signal.SIGTERM, signal.SIGBREAK]
    # a closed terminal does not reach the processes in their own groups
    return [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]
