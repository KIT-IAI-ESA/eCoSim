from dataclasses import dataclass

from ecosim_common.tech.parallel import error_recording_thread


@dataclass
class ErrorRecordingThread(error_recording_thread.ErrorRecordingThread):
    def assert_ends_within(self, timeout_in_seconds: float) -> None:
        self._thread.join(timeout_in_seconds)
        assert not self._thread.is_alive(), f"the thread still runs after {timeout_in_seconds}s"
