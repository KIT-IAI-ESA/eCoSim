import socket

import pytest

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.socket import tcp_socket
from ecosim_common.communication.socket.tcp_socket import TCPSocket
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS
from tests.communication.socket.failing_sockets import SocketWhoseShutdownDoesNotWakeAccept
from tests.communication.socket.socket_test_setup import ignore_connection

pytestmark = pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")


def test_close_ends_a_blocked_accept_and_frees_the_port(address: ConnectionAddress) -> None:
    internal_socket = SocketWhoseShutdownDoesNotWakeAccept()
    blocked_listener = TCPSocket(_internal_socket=internal_socket, _connection_address=address)
    blocked_listener.listen_on_connection_loop_async(channel_handler=ignore_connection)
    assert internal_socket.accept_entered.wait(timeout=WAIT_TIMEOUT_IN_SECONDS)

    blocked_listener.close()

    assert internal_socket.fileno() == -1
    assert not blocked_listener.is_listening_on_connection_event().is_set()
    with socket.create_server((address.ip, address.port)):
        pass


def test_a_stuck_accept_loop_does_not_hold_up_close(address: ConnectionAddress, monkeypatch: pytest.MonkeyPatch) -> None:
    """The accept timeout outlasts the wait in close(), so the accept loop is still running when close() returns."""
    monkeypatch.setattr(target=tcp_socket, name="ACCEPT_TIMEOUT_IN_SECONDS", value=1)
    monkeypatch.setattr(target=tcp_socket, name="ACCEPT_LOOP_END_TIMEOUT_IN_SECONDS", value=0)
    internal_socket = SocketWhoseShutdownDoesNotWakeAccept()
    stuck_listener = TCPSocket(_internal_socket=internal_socket, _connection_address=address)
    stuck_listener.listen_on_connection_loop_async(channel_handler=ignore_connection)
    assert internal_socket.accept_entered.wait(timeout=WAIT_TIMEOUT_IN_SECONDS)

    stuck_listener.close()

    assert stuck_listener.is_listening_on_connection_event().is_set()
