import errno
import queue
import socket
import threading
from typing import Iterator

import pytest

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ConnectionData
from ecosim_common.communication.socket.tcp_socket import TCPSocket
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS
from tests.communication.socket.socket_test_setup import LOOPBACK_IP, ignore_connection

pytestmark = pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")


@pytest.fixture
def connections() -> "queue.Queue[ConnectionData]":
    return queue.Queue()


@pytest.fixture
def listener(address: ConnectionAddress, connections: "queue.Queue[ConnectionData]") -> Iterator[TCPSocket]:
    def collect_connection(connection_data: ConnectionData) -> None:
        connections.put(connection_data)

    listening_socket = TCPSocket.create(address)
    listening_socket.listen_on_connection_loop_async(channel_handler=collect_connection)
    yield listening_socket
    listening_socket.close()


def test_listening_on_a_busy_port_leaves_nothing_behind() -> None:
    internal_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    with socket.create_server((LOOPBACK_IP, 0)) as occupant:
        busy_address = ConnectionAddress(ip=LOOPBACK_IP, port=occupant.getsockname()[1])
        busy_listener = TCPSocket(_internal_socket=internal_socket, _connection_address=busy_address)

        with pytest.raises(OSError) as error:
            busy_listener.listen_on_connection_loop_async(channel_handler=ignore_connection)

    assert error.value.errno == errno.EADDRINUSE
    assert internal_socket.fileno() == -1
    assert not busy_listener.is_listening_on_connection_event().is_set()


def test_second_listen_call_changes_nothing(listener: TCPSocket) -> None:
    threads_before = set(threading.enumerate())

    listener.listen_on_connection_loop_async(channel_handler=ignore_connection)

    assert set(threading.enumerate()) <= threads_before


@pytest.mark.usefixtures("listener")
def test_connection_from_the_bound_ip_reaches_the_handler(address: ConnectionAddress, connections: "queue.Queue[ConnectionData]") -> None:
    with socket.create_connection((address.ip, address.port), timeout=WAIT_TIMEOUT_IN_SECONDS) as client:
        connection_data = connections.get(timeout=WAIT_TIMEOUT_IN_SECONDS)

        assert connection_data.client_address == ConnectionAddress.of_raw_socket_address(client.getsockname())
