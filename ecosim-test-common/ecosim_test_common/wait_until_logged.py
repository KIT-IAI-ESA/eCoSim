import time

import pytest


def wait_until_logged(caplog: pytest.LogCaptureFixture, message_start: str, timeout_in_seconds: float) -> None:
    deadline = time.monotonic() + timeout_in_seconds
    while not any(message.startswith(message_start) for message in caplog.messages):
        if time.monotonic() > deadline:
            raise TimeoutError(f"No message starting with '{message_start}' was logged within {timeout_in_seconds}s")
        time.sleep(0.1)
