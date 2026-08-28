import threading

import dask.distributed as dd
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from integration_tests.communication.message_data_for_test import MessageDataForTest

_RECEIVE_TIMEOUT_IN_SECONDS = 3
# how long a 'listen_blocking' may overshoot its timeout before the test declares the timeout ignored
_TOLERANCE_IN_SECONDS = 10


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

    assert _listen_blocking_bounded(channel) is None


def test_listen_blocking_returns_after_the_given_timeout(dask_client: dd.Client) -> None:
    """The caller decides how long it waits - the channel must not fall back to its own timeout."""
    assert _listen_blocking_bounded(_connected_channel()) is None


def _connected_channel() -> ESPChannel:
    return ESPChannelConnector(CommunicationProtocol.DASK).connect(
        connection_address=ConnectionAddress(ip="localhost", port=8786),
    )


def _listen_blocking_bounded(channel: ESPChannel) -> ESPChannelMessage | None:
    """Fails instead of hanging if 'listen_blocking' does not honour '_RECEIVE_TIMEOUT_IN_SECONDS'."""
    received: list[ESPChannelMessage | None] = []

    def receive() -> None:
        received.append(channel.listen_blocking(timeout_in_seconds=_RECEIVE_TIMEOUT_IN_SECONDS))

    thread = threading.Thread(target=receive, daemon=True)
    thread.start()
    thread.join(timeout=_RECEIVE_TIMEOUT_IN_SECONDS + _TOLERANCE_IN_SECONDS)
    assert not thread.is_alive(), "'listen_blocking' did not return within its timeout"
    return received[0]
