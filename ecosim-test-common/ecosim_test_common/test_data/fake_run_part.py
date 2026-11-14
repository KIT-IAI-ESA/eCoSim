import sys
import textwrap
from dataclasses import dataclass


@dataclass(frozen=True)
class FakeRunPart:
    """A part of a run that prints 'ready' once it handles signals, and 'exit <code>' when one ends it."""

    exit_code: int = 0
    # None runs until a signal ends it
    seconds: float | None = None
    ignores_the_stop: bool = False
    # like 44 for a part on Windows, which ecosim run stops with a break signal
    exit_code_of_a_stop: int | None = None
    seconds_to_stop: float = 0
    # printed before it ends on its own, like a log line of the server
    last_line: str = ""

    def command(self) -> list[str]:
        return [sys.executable, "-c", self._script()]

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
                time.sleep({self.seconds if self.seconds is not None else 3600})
            except SystemExit as stopped:
                time.sleep({self.seconds_to_stop})
                print(f"exit {{stopped.code}}", flush=True)
                raise
            print({self.last_line!r}, flush=True)
            sys.exit({self.exit_code})
            """,
        )
