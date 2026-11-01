import socket
import threading
from contextlib import contextmanager
from typing import Iterator
from unittest.mock import Mock

import dask.distributed as dd
import distributed
import pytest

from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.socket.tcp_socket import TCPSocket
from tests.communication.channel_test_setup import (
    ADDRESS,
    BOUND_IN_SECONDS,
    SHORT_TIMEOUT_IN_SECONDS,
    dask_channel_pair,
    listen_blocking_bounded,
    simple_message,
)

_HANDLER_ERROR = "the handler failed"
_EARLIER_TIMEOUT_IN_SECONDS = 7


def _raise_handler_error(message: ESPChannelMessage) -> None:
    raise RuntimeError(_HANDLER_ERROR)


@contextmanager
def _connected_sockets() -> Iterator[tuple[socket.socket, socket.socket]]:
    with socket.create_server(("127.0.0.1", 0)) as server:
        connecting_end = socket.create_connection(server.getsockname())
        accepted_end, _ = server.accept()
    with connecting_end, accepted_end:
        yield connecting_end, accepted_end


@pytest.fixture
def channel_and_peer(communication_protocol: CommunicationProtocol) -> Iterator[tuple[ESPChannel, ESPChannel]]:
    if communication_protocol is CommunicationProtocol.DASK:
        yield dask_channel_pair()
        return
    with _connected_sockets() as (connecting_end, accepted_end):
        channel = TCPSocket(_internal_socket=connecting_end, _connection_address=ADDRESS)
        peer = TCPSocket(_internal_socket=accepted_end, _connection_address=ADDRESS)
        yield channel, peer
        channel.close()
        peer.close()


def _finishes_in_time(channel: ESPChannel) -> bool:
    waiting = threading.Thread(target=channel.wait_for_finish, daemon=True)
    waiting.start()
    waiting.join(timeout=BOUND_IN_SECONDS)
    return not waiting.is_alive()


def test_a_raising_handler_closes_the_channel(channel_and_peer: tuple[ESPChannel, ESPChannel], caplog: pytest.LogCaptureFixture) -> None:
    channel, peer = channel_and_peer
    channel.listen_on_message_async(on_message=_raise_handler_error)

    peer.send(simple_message())

    assert _finishes_in_time(channel), "the listener thread died and left the channel open"
    assert listen_blocking_bounded(channel=peer, timeout_in_seconds=BOUND_IN_SECONDS) is None, "the peer was not told that the channel closed"
    assert _HANDLER_ERROR in caplog.text
    assert "Traceback" in caplog.text


def test_a_receive_timeout_raises_and_leaves_the_channel_usable(channel_and_peer: tuple[ESPChannel, ESPChannel]) -> None:
    channel, peer = channel_and_peer

    with pytest.raises(TimeoutError):
        listen_blocking_bounded(channel=channel, timeout_in_seconds=SHORT_TIMEOUT_IN_SECONDS)

    peer.send(simple_message())
    assert listen_blocking_bounded(channel=channel, timeout_in_seconds=BOUND_IN_SECONDS) is not None


def test_a_receive_timeout_restores_the_earlier_socket_timeout() -> None:
    with _connected_sockets() as (connecting_end, _):
        connecting_end.settimeout(_EARLIER_TIMEOUT_IN_SECONDS)
        channel = TCPSocket(_internal_socket=connecting_end, _connection_address=ADDRESS)

        with pytest.raises(TimeoutError):
            listen_blocking_bounded(channel=channel, timeout_in_seconds=SHORT_TIMEOUT_IN_SECONDS)

        timeout_after_the_wait = connecting_end.gettimeout()
        channel.close()

    assert timeout_after_the_wait == _EARLIER_TIMEOUT_IN_SECONDS


def test_listen_blocking_returns_none_when_the_peer_closes(channel_and_peer: tuple[ESPChannel, ESPChannel]) -> None:
    channel, peer = channel_and_peer

    peer.close()

    assert listen_blocking_bounded(channel=channel, timeout_in_seconds=BOUND_IN_SECONDS) is None


def test_a_receive_error_closes_the_tcp_channel() -> None:
    internal_socket = Mock(spec=socket.socket)
    internal_socket.recv.side_effect = ConnectionResetError("connection lost")
    channel = TCPSocket(_internal_socket=internal_socket, _connection_address=ADDRESS)

    channel.listen_on_message_async(on_message=Mock())

    assert _finishes_in_time(channel)


def test_a_receive_error_closes_the_dask_channel(dask_client: dd.Client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(distributed.Queue, "get", Mock(side_effect=OSError("scheduler lost")))
    channel, _ = dask_channel_pair()

    channel.listen_on_message_async(on_message=Mock())

    assert _finishes_in_time(channel)
