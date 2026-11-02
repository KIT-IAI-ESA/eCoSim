import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Iterator
from unittest.mock import Mock

import dask.distributed as dd
import pytest

from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_test_common.bounded_listen import BOUND_IN_SECONDS
from tests.communication.channel_test_setup import dask_channel_pair

_SCHEDULER_START_TIMEOUT_IN_SECONDS = 30
_CONNECT_TIMEOUT_IN_SECONDS = 3


@pytest.fixture
def scheduler_process_with_client() -> Iterator[subprocess.Popen[bytes]]:
    port = get_free_port()
    command = [sys.executable, "-m", "distributed.cli.dask_scheduler", "--host", "127.0.0.1", "--port", str(port), "--no-dashboard"]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    address = f"tcp://127.0.0.1:{port}"
    # the first client only waits for the start, the second one sets how long a lost scheduler blocks a call
    dd.Client(address=address, timeout=_SCHEDULER_START_TIMEOUT_IN_SECONDS).close()
    client = dd.Client(address=address, timeout=_CONNECT_TIMEOUT_IN_SECONDS)
    yield process
    client.close()
    process.kill()
    process.wait()
    # the channels are shutdown listeners that can no longer close
    ShutdownManager.reset_instance()


def test_a_lost_scheduler_raises_in_the_waiters_and_ends_the_listener(scheduler_process_with_client: subprocess.Popen[bytes]) -> None:
    """The events of a channel live on the scheduler, so it cannot close: its waiters get the error instead."""
    channel, _ = dask_channel_pair()
    with ThreadPoolExecutor() as executor:
        listener = executor.submit(channel._listen_on_message, on_message=Mock())  # noqa: SLF001
        waiter = executor.submit(channel.wait_for_finish)
        assert channel.is_listening_event().wait(timeout=BOUND_IN_SECONDS)

        scheduler_process_with_client.kill()

        assert isinstance(waiter.exception(timeout=BOUND_IN_SECONDS), OSError), "the waiter was not told"
        assert listener.exception(timeout=BOUND_IN_SECONDS) is None, "the listener died on an uncaught error"
