from __future__ import annotations

import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

from ecosim.run.run_part import PartToStart, RunPart
from ecosim.run.run_watch import RunEnd, RunWatch
from ecosim.run.server_log_follower import ServerLogFollower


@dataclass(frozen=True)
class RunOutcome:
    end: RunEnd
    exit_code: int
    seconds: float


@dataclass(frozen=True)
class LocalRun:
    """The server and a client for each simulator, each in a process group of its own."""

    server: PartToStart
    clients: list[PartToStart]
    seconds_to_stop: float = 10
    # after the server ended, the clients end right after its stop message
    seconds_for_the_clients_to_end: float = 15
    # short, since Windows does not interrupt a longer wait for a Ctrl-C
    seconds_between_looks: float = 0.5

    def execute(self, working_folder: Path, environment: dict[str, str]) -> RunOutcome:
        started_at = time.monotonic()
        signals: list[tuple[int, float]] = []

        def take_note(signal_number: int, frame: FrameType | None) -> None:
            # the watch handles the signal at its next look, so the handler waits for nothing
            signals.append((signal_number, time.monotonic()))

        # before the first part starts, so no signal is missed
        previous_handlers = {signal_number: signal.signal(signal_number, take_note) for signal_number in _stop_signals()}
        try:
            watch = self._watch_until_the_end(working_folder=working_folder, environment=environment, signals=signals)
        finally:
            for signal_number, previous_handler in previous_handlers.items():
                signal.signal(signal_number, previous_handler)
        # once the server has ended, the watch knows whether the run finished
        return RunOutcome(end=watch.end or RunEnd.FAILED, exit_code=watch.exit_code(), seconds=time.monotonic() - started_at)

    def _watch_until_the_end(self, working_folder: Path, environment: dict[str, str], signals: list[tuple[int, float]]) -> RunWatch:
        started: list[RunPart] = []
        try:
            # one by one, so a part that cannot start leaves no other part running
            for part_to_start in [self.server, *self.clients]:
                started.append(part_to_start.start(working_folder=working_folder, environment=environment))
            watch = RunWatch(
                server=started[0],
                clients=started[1:],
                follower=ServerLogFollower(log_file=started[0].log_file, read_up_to=started[0].log_start),
                seconds_to_stop=self.seconds_to_stop,
                seconds_for_the_clients_to_end=self.seconds_for_the_clients_to_end,
            )
            while watch.is_running():
                watch.look(signals=signals)
                time.sleep(self.seconds_between_looks)
            watch.look(signals=signals)
        except BaseException:
            # without ecosim run nothing would stop the parts that run
            for part in started:
                part.kill()
            raise
        return watch


def _stop_signals() -> list[signal.Signals]:
    # a stop that Windows sends to a process group arrives as SIGBREAK
    if sys.platform == "win32":
        return [signal.SIGINT, signal.SIGTERM, signal.SIGBREAK]
    # a closed terminal or a lost SSH connection does not reach the parts in their own process groups
    return [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]
