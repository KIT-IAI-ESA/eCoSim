import threading
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class ErrorRecordingThread:
    """A daemon thread that keeps what its target raises."""

    target: Callable[[], None]
    name: str | None = None
    error: Exception | None = field(default=None, init=False)
    _thread: threading.Thread = field(init=False)

    def __post_init__(self) -> None:
        self._thread = threading.Thread(target=self._run_target, name=self.name, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def ends_within(self, timeout_in_seconds: float) -> bool:
        self._thread.join(timeout=timeout_in_seconds)
        return not self._thread.is_alive()

    def _run_target(self) -> None:
        try:
            self.target()
        except Exception as error:
            self.error = error
