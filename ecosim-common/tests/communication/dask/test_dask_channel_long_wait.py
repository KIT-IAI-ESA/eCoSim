import time

import dask.distributed as dd
import pytest

from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_test_common.bounded_listen import listen_blocking_bounded, listen_blocking_in_background
from ecosim_test_common.timeouts import SHORT_TIMEOUT_IN_SECONDS, WAIT_TIMEOUT_IN_SECONDS
from tests.communication.channel_test_setup import ADDRESS, SlowEchoHandler, dask_channel_pair, simple_message


@pytest.fixture(autouse=True)
def short_receive_retry_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(DaskChannel, "_RECEIVE_RETRY_INTERVAL_IN_SECONDS", SHORT_TIMEOUT_IN_SECONDS)


def test_a_wait_without_timeout_gets_an_answer_that_takes_longer_than_the_retry_interval(dask_client: dd.Client) -> None:
    connector, listener = dask_channel_pair()
    listener.listen_on_message_async(on_message=SlowEchoHandler(channel=listener, delay_in_seconds=3))

    connector.send(message=simple_message())

    assert listen_blocking_bounded(channel=connector) is not None, "the wait gave up before the answer came"


def test_closing_ends_a_wait_in_progress_that_gets_no_close_signal(dask_client: dd.Client) -> None:
    """A channel that never connected writes no sentinel on close, so only the retry can notice the close."""
    channel = DaskChannel.of(connection_address=ADDRESS)
    wait = listen_blocking_in_background(channel=channel)
    time.sleep(SHORT_TIMEOUT_IN_SECONDS)
    assert wait.empty(), "the wait ended before the close"

    channel.close()

    assert wait.get(timeout=WAIT_TIMEOUT_IN_SECONDS) is None
