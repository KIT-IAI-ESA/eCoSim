import threading
from typing import Callable

from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS


def finishes_in_time(blocking_call: Callable[[], None]) -> bool:
    waiting = threading.Thread(target=blocking_call, daemon=True)
    waiting.start()
    waiting.join(timeout=WAIT_TIMEOUT_IN_SECONDS)
    return not waiting.is_alive()
