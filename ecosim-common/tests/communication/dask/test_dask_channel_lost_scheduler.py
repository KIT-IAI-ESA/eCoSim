import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Iterator
from unittest.mock import Mock

import dask.distributed as dd
import pytest

from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.tech.port_utils import get_free_port
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS
from tests.communication.channel_test_setup import ADDRESS, LostSchedulerEvent, dask_channel_pair


@pytest.fixture
def scheduler_process_with_client() -> Iterator[subprocess.Popen[bytes]]:
    port = get_free_port()
    command = [sys.executable, "-m", "distributed.cli.dask_scheduler", "--host", "127.0.0.1", "--port", str(port), "--no-dashboard"]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    address = f"tcp://127.0.0.1:{port}"
    # the first client only waits for the start, the second one sets how long a lost scheduler blocks a call
    dd.Client(address=address, timeout=30).close()
    client = dd.Client(address=address, timeout=3)
    yield process
    client.close()
    process.kill()
    process.wait()


def test_a_lost_scheduler_raises_in_the_waiters_and_ends_the_receive_loop(scheduler_process_with_client: subprocess.Popen[bytes]) -> None:
    """The events of a channel live on the scheduler, so it cannot close: its waiters get the error instead."""
    channel, _ = dask_channel_pair()
    with ThreadPoolExecutor() as executor:
        receive_loop = executor.submit(channel._listen_on_message, on_message=Mock())  # noqa: SLF001
        waiter = executor.submit(channel.wait_for_finish)
        assert channel.is_listening_event().wait(timeout=WAIT_TIMEOUT_IN_SECONDS)

        scheduler_process_with_client.kill()

        assert isinstance(waiter.exception(timeout=WAIT_TIMEOUT_IN_SECONDS), OSError), "the waiter was not told"
        assert receive_loop.exception(timeout=WAIT_TIMEOUT_IN_SECONDS) is None, "the receive loop died on an uncaught error"


def test_a_closed_client_ends_the_receive_loop_without_an_uncaught_error(scheduler_process_with_client: subprocess.Popen[bytes]) -> None:
    channel, _ = dask_channel_pair()
    with ThreadPoolExecutor() as executor:
        receive_loop = executor.submit(channel._listen_on_message, on_message=Mock())  # noqa: SLF001
        assert channel.is_listening_event().wait(timeout=WAIT_TIMEOUT_IN_SECONDS)

        dd.default_client().close()

        assert receive_loop.exception(timeout=WAIT_TIMEOUT_IN_SECONDS) is None, "the receive loop died on an uncaught error"


def test_closing_a_channel_after_its_scheduler_is_lost_does_not_raise(scheduler_process_with_client: subprocess.Popen[bytes]) -> None:
    channel, _ = dask_channel_pair()
    scheduler_process_with_client.kill()
    scheduler_process_with_client.wait()

    channel.close()


def test_closing_a_channel_does_not_raise_when_the_scheduler_is_lost_before_the_client_notices(dask_client: dd.Client) -> None:
    channel = DaskChannel(_connection_address=ADDRESS, _is_finished=LostSchedulerEvent())

    channel.close()
