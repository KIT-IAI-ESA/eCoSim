import threading

from ecosim_common.client.client import Client
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS


def wait_until_finished_bounded(client: Client) -> None:
    waiting = threading.Thread(target=client.wait_until_finished, daemon=True)
    waiting.start()
    waiting.join(timeout=WAIT_TIMEOUT_IN_SECONDS)
    if waiting.is_alive():
        raise TimeoutError(f"The client was still waiting for its run to finish after {WAIT_TIMEOUT_IN_SECONDS}s.")
