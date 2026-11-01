import queue
import time

import dask.distributed as dd
import pytest

from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.dask import dask_channel
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.communication.message_type import MessageType
from tests.communication.channel_test_setup import (
    ADDRESS,
    BOUND_IN_SECONDS,
    SHORT_TIMEOUT_IN_SECONDS,
    dask_channel_pair,
    listen_blocking_bounded,
    simple_message,
)

_STEP_IN_SECONDS = 3


@pytest.fixture(autouse=True)
def short_receive_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dask_channel, "_DEFAULT_RECEIVE_TIMEOUT_IN_SECONDS", SHORT_TIMEOUT_IN_SECONDS)


def test_an_idle_listener_outlasts_the_receive_timeout(dask_client: dd.Client) -> None:
    channel, peer = dask_channel_pair()
    received: queue.Queue[ESPChannelMessage] = queue.Queue()
    channel.listen_on_message_async(on_message=received.put)

    time.sleep(_STEP_IN_SECONDS)
    peer.send(simple_message())

    assert received.get(timeout=BOUND_IN_SECONDS).type() is MessageType.SIMULATION_STEP


def test_a_step_longer_than_the_receive_timeout_reaches_the_waiting_side(dask_client: dd.Client) -> None:
    waiting_side, stepping_side = dask_channel_pair()

    def run_step(message: ESPChannelMessage) -> None:
        time.sleep(_STEP_IN_SECONDS)
        stepping_side.send(message)

    stepping_side.listen_on_message_async(on_message=run_step)
    waiting_side.send(simple_message())

    assert listen_blocking_bounded(waiting_side) is not None, "the wait for a long step was taken for the close signal"


def test_closing_ends_a_wait_that_got_no_close_signal(dask_client: dd.Client) -> None:
    never_connected = DaskChannel.of(connection_address=ADDRESS)

    never_connected.close()

    assert listen_blocking_bounded(never_connected) is None
