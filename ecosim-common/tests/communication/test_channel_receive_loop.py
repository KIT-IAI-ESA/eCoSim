import logging
import socket
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import Mock

import pytest

from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.socket.tcp_socket import TCPSocket
from ecosim_test_common.bounded_listen import listen_blocking_bounded
from ecosim_test_common.bounded_wait import finishes_in_time
from ecosim_test_common.timeouts import SHORT_TIMEOUT_IN_SECONDS, WAIT_TIMEOUT_IN_SECONDS
from tests.communication.channel_test_setup import ADDRESS, RaisingMessageHandler, dask_channel_pair, simple_message


@contextmanager
def _connected_sockets() -> Iterator[tuple[socket.socket, socket.socket]]:
    with socket.create_server(("127.0.0.1", 0)) as server:
        connector = socket.create_connection(server.getsockname())
        listener, _ = server.accept()
    with connector, listener:
        yield connector, listener


@pytest.fixture
def channel_and_peer(communication_protocol: CommunicationProtocol) -> Iterator[tuple[ESPChannel, ESPChannel]]:
    if communication_protocol is CommunicationProtocol.DASK:
        yield dask_channel_pair()
        return
    with _connected_sockets() as (connector, listener):
        channel = TCPSocket(_internal_socket=connector, _connection_address=ADDRESS)
        peer = TCPSocket(_internal_socket=listener, _connection_address=ADDRESS)
        yield channel, peer
        channel.close()
        peer.close()


def test_a_raising_handler_closes_the_channel(channel_and_peer: tuple[ESPChannel, ESPChannel]) -> None:
    channel, peer = channel_and_peer
    handler = RaisingMessageHandler()
    channel.listen_on_message_async(on_message=handler)

    peer.send(simple_message())

    assert finishes_in_time(blocking_call=channel.wait_for_finish), "the listen thread died and left the channel open"
    assert handler.call_count == 1
    assert listen_blocking_bounded(channel=peer, timeout_in_seconds=WAIT_TIMEOUT_IN_SECONDS) is None, "the peer was not told that the channel closed"


def _log_of_a_raising_handler(channel_and_peer: tuple[ESPChannel, ESPChannel], caplog: pytest.LogCaptureFixture) -> str:
    channel, peer = channel_and_peer
    channel.listen_on_message_async(on_message=RaisingMessageHandler())

    peer.send(simple_message())

    assert finishes_in_time(blocking_call=channel.wait_for_finish), "the listen thread died and left the channel open"
    return caplog.text


def test_the_swallowed_error_of_a_handler_is_logged_in_one_line_without_debug(
    channel_and_peer: tuple[ESPChannel, ESPChannel],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)

    log = _log_of_a_raising_handler(channel_and_peer=channel_and_peer, caplog=caplog)

    assert RaisingMessageHandler.ERROR_MESSAGE in log
    assert "Traceback" not in log


def test_the_swallowed_error_of_a_handler_is_logged_with_its_traceback_with_debug(
    channel_and_peer: tuple[ESPChannel, ESPChannel],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)

    assert "Traceback" in _log_of_a_raising_handler(channel_and_peer=channel_and_peer, caplog=caplog)


def test_a_receive_timeout_raises_and_leaves_the_channel_usable(channel_and_peer: tuple[ESPChannel, ESPChannel]) -> None:
    channel, peer = channel_and_peer

    with pytest.raises(TimeoutError):
        listen_blocking_bounded(channel=channel, timeout_in_seconds=SHORT_TIMEOUT_IN_SECONDS)

    peer.send(simple_message())
    assert listen_blocking_bounded(channel=channel, timeout_in_seconds=WAIT_TIMEOUT_IN_SECONDS) is not None


def test_a_receive_timeout_restores_the_earlier_socket_timeout() -> None:
    earlier_timeout_in_seconds = 7
    with _connected_sockets() as (connector, _):
        connector.settimeout(earlier_timeout_in_seconds)
        channel = TCPSocket(_internal_socket=connector, _connection_address=ADDRESS)

        with pytest.raises(TimeoutError):
            listen_blocking_bounded(channel=channel, timeout_in_seconds=SHORT_TIMEOUT_IN_SECONDS)

        timeout_after_the_wait = connector.gettimeout()
        channel.close()

    assert timeout_after_the_wait == earlier_timeout_in_seconds


def test_listen_blocking_returns_none_when_the_peer_closes(channel_and_peer: tuple[ESPChannel, ESPChannel]) -> None:
    channel, peer = channel_and_peer

    peer.close()

    assert listen_blocking_bounded(channel=channel, timeout_in_seconds=WAIT_TIMEOUT_IN_SECONDS) is None


def test_a_receive_error_closes_the_tcp_channel() -> None:
    internal_socket = Mock(spec=socket.socket)
    internal_socket.recv.side_effect = ConnectionResetError("connection lost")
    channel = TCPSocket(_internal_socket=internal_socket, _connection_address=ADDRESS)

    channel.listen_on_message_async(on_message=Mock())

    assert finishes_in_time(blocking_call=channel.wait_for_finish)
