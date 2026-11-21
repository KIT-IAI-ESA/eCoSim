from dataclasses import dataclass

from ecosim_common.tech.parallel import error_recording_thread


@dataclass
class ErrorRecordingThread(error_recording_thread.ErrorRecordingThread):
    def assert_ends_within(self, timeout_in_seconds: float) -> None:
        assert self.ends_within(timeout_in_seconds=timeout_in_seconds), f"the thread still runs after {timeout_in_seconds}s"
