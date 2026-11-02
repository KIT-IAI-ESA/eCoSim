import threading

# below the per-test 'timeout' in pyproject.toml, so a hang fails here with a message and not at that limit
SERVER_FINISH_TIMEOUT_IN_SECONDS = 110


def assert_server_finishes_in_time(server_thread: threading.Thread) -> None:
    server_thread.join(timeout=SERVER_FINISH_TIMEOUT_IN_SECONDS)
    assert not server_thread.is_alive(), f"The server did not finish within {SERVER_FINISH_TIMEOUT_IN_SECONDS}s"
