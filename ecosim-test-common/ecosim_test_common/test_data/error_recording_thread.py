import threading
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ErrorRecordingThread:
    """Keeps what the target raises. A daemon thread, so a target that hangs fails its test and not the whole test run."""

    target: Callable[[], None]
    error: Exception | None = field(default=None, init=False)
    _thread: threading.Thread = field(init=False)

    def __post_init__(self) -> None:
        self._thread = threading.Thread(target=self._run_target, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def assert_ends_within(self, limit_in_seconds: float) -> None:
        self._thread.join(limit_in_seconds)
        assert not self._thread.is_alive(), f"the thread still runs after {limit_in_seconds}s"

    def _run_target(self) -> None:
        try:
            self.target()
        except Exception as error:
            self.error = error
