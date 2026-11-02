import time

import dask.distributed as dd
import pytest
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_test_common.bounded_listen import listen_blocking_bounded
from integration_tests.communication.message_data_for_test import MessageDataForTest

_RECEIVE_TIMEOUT_IN_SECONDS = 3


def test_a_channel_does_not_receive_its_own_message(dask_client: dd.Client) -> None:
    """
    Every endpoint reads its own inbox, so a sender can never pick up what it just sent.
    """
    channel = _connected_channel()
    channel.send(
        ESPChannelMessageJson.create(
            type=MessageType.CLIENT_META_DATA_REQUEST,
            correlation_id=CorrelationId.of_int(1),
            payload=MessageDataForTest(string="own message", integer=1),
        ),
    )

    with pytest.raises(TimeoutError):
        listen_blocking_bounded(channel=channel, timeout_in_seconds=_RECEIVE_TIMEOUT_IN_SECONDS)


def test_listen_blocking_times_out_after_the_given_timeout(dask_client: dd.Client) -> None:
    """The caller decides how long it waits - the channel must not fall back to its own timeout."""
    channel = _connected_channel()
    started_at = time.monotonic()

    with pytest.raises(TimeoutError):
        listen_blocking_bounded(channel=channel, timeout_in_seconds=_RECEIVE_TIMEOUT_IN_SECONDS)

    assert time.monotonic() - started_at >= _RECEIVE_TIMEOUT_IN_SECONDS, "'listen_blocking' gave up before its timeout"


def _connected_channel() -> ESPChannel:
    return ESPChannelConnector(CommunicationProtocol.DASK).connect(
        connection_address=ConnectionAddress(ip="localhost", port=8786),
    )
