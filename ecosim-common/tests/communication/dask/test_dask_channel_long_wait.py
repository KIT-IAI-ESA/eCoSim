import time
from unittest.mock import Mock

import dask.distributed as dd
import distributed
import pytest

from ecosim_common.communication.binary_message.simple_binary_message import SimpleBinaryMessage
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.communication.message_type import MessageType
from ecosim_test_common.bounded_listen import BOUND_IN_SECONDS, listen_blocking_bounded, listen_blocking_in_background
from tests.communication.channel_test_setup import ADDRESS, SHORT_TIMEOUT_IN_SECONDS, SlowEchoHandler, dask_channel_pair, simple_message

_STEP_IN_SECONDS = 3


@pytest.fixture(autouse=True)
def short_receive_retry_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(DaskChannel, "_RECEIVE_RETRY_INTERVAL_IN_SECONDS", SHORT_TIMEOUT_IN_SECONDS)


def test_silence_does_not_end_a_wait_without_timeout(dask_client: dd.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    raw_message = SimpleBinaryMessage.of_esp_channel_message(message=simple_message()).raw_message()
    inbox_get = Mock(side_effect=[TimeoutError(), raw_message])
    monkeypatch.setattr(distributed.Queue, "get", inbox_get)
    channel, _ = dask_channel_pair()

    message = listen_blocking_bounded(channel)

    assert inbox_get.call_count == 2, "the wait did not ask again after the silence"
    assert message is not None, "the silence was taken for the close signal"
    assert message.type() is MessageType.SIMULATION_STEP


def test_the_waiting_side_gets_the_answer_of_a_step_longer_than_the_retry_interval(dask_client: dd.Client) -> None:
    waiting_side, stepping_side = dask_channel_pair()
    stepping_side.listen_on_message_async(on_message=SlowEchoHandler(channel=stepping_side, delay_in_seconds=_STEP_IN_SECONDS))

    waiting_side.send(simple_message())

    assert listen_blocking_bounded(waiting_side) is not None, "the wait for a long step was taken for the close signal"


def test_closing_ends_a_wait_in_progress_that_gets_no_close_signal(dask_client: dd.Client) -> None:
    """A channel that never connected writes no sentinel on close, so only the retry can notice the close."""
    never_connected = DaskChannel.of(connection_address=ADDRESS)
    wait = listen_blocking_in_background(never_connected)
    time.sleep(SHORT_TIMEOUT_IN_SECONDS)
    assert wait.empty(), "the wait ended before the close"

    never_connected.close()

    assert wait.get(timeout=BOUND_IN_SECONDS) is None
