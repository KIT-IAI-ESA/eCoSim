import socket
import threading
from itertools import chain, repeat
from typing import Iterator
from unittest.mock import Mock

import pytest

from ecosim_common.communication.binary_message import binary_message_header
from ecosim_common.communication.binary_message.binary_message_header import BinaryMessageHeader
from ecosim_common.communication.binary_message.received_binary_messages import ReceivedBinaryMessage
from ecosim_common.communication.binary_message.simple_binary_message import SimpleBinaryMessage
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.socket.tcp_socket import TCPSocket

ADDRESS = ConnectionAddress(ip="127.0.0.1", port=1234)
CORRELATION_ID = CorrelationId.of_int(4_294_967_295)
HEADER_BYTES = binary_message_header.HEADER_BYTES
EMPTY_AND_LARGE_PAYLOADS = [b"", b"x" * 70_000]
# more than the buffers of a TCP connection hold, so a single send() cannot take it all
LARGER_THAN_THE_SOCKET_BUFFERS = 32 * 1024 * 1024


def _raw_message(payload: bytes) -> bytes:
    return SimpleBinaryMessage(
        _type=MessageType.SIMULATION_STEP,
        _correlation_id=CORRELATION_ID,
        _payload=payload,
    ).raw_message()


def _received_message(payload: bytes) -> ReceivedBinaryMessage:
    return ReceivedBinaryMessage(
        _header=BinaryMessageHeader(_raw_message(payload=payload)[:HEADER_BYTES]),
        _data=payload,
    )


def _socket_receiving(stream: bytes) -> TCPSocket:
    """TCP may split a stream anywhere, so this socket hands out one byte per recv() and then b"" like a closed connection."""
    internal_socket = Mock(spec=socket.socket)
    internal_socket.recv.side_effect = chain((bytes([byte]) for byte in stream), repeat(b""))
    return TCPSocket(_internal_socket=internal_socket, _connection_address=ADDRESS)


@pytest.fixture
def sender_and_receiver() -> Iterator[tuple[TCPSocket, TCPSocket]]:
    with socket.create_server(("127.0.0.1", 0)) as server:
        sending_end = socket.create_connection(server.getsockname())
        receiving_end, _ = server.accept()
    with sending_end, receiving_end:
        # with a timeout Python keeps the socket non-blocking, so a full buffer makes send() return a short write
        sending_end.settimeout(10)
        receiving_end.settimeout(10)
        sender = TCPSocket(_internal_socket=sending_end, _connection_address=ADDRESS)
        receiver = TCPSocket(_internal_socket=receiving_end, _connection_address=ADDRESS)
        yield sender, receiver
        sender.close()
        receiver.close()


@pytest.mark.parametrize("payload", EMPTY_AND_LARGE_PAYLOADS, ids=["empty", "large"])
def test_header_round_trip(payload: bytes) -> None:
    header = BinaryMessageHeader(_raw_message(payload=payload)[:HEADER_BYTES])

    assert header.correlation_id == CORRELATION_ID
    assert header.message_type is MessageType.SIMULATION_STEP
    assert header.data_length == len(payload)


@pytest.mark.parametrize("payload", EMPTY_AND_LARGE_PAYLOADS, ids=["empty", "large"])
def test_receive_reads_a_message_arriving_one_byte_at_a_time(payload: bytes) -> None:
    tcp_socket = _socket_receiving(stream=_raw_message(payload=payload))

    assert tcp_socket.receive() == _received_message(payload=payload)


def test_receive_keeps_consecutive_messages_apart() -> None:
    tcp_socket = _socket_receiving(stream=_raw_message(payload=b"first") + _raw_message(payload=b"second"))

    assert tcp_socket.receive() == _received_message(payload=b"first")
    assert tcp_socket.receive() == _received_message(payload=b"second")


def test_receive_returns_none_when_the_connection_closes_between_messages() -> None:
    tcp_socket = _socket_receiving(stream=_raw_message(payload=b"only"))

    assert tcp_socket.receive() == _received_message(payload=b"only")
    assert tcp_socket.receive() is None


@pytest.mark.parametrize("received_bytes", [1, HEADER_BYTES - 1, HEADER_BYTES, HEADER_BYTES + 1])
def test_receive_raises_when_the_connection_closes_inside_a_message(received_bytes: int) -> None:
    tcp_socket = _socket_receiving(stream=_raw_message(payload=b"cut off")[:received_bytes])

    with pytest.raises(ConnectionError):
        tcp_socket.receive()


def test_send_delivers_a_message_larger_than_the_socket_buffers(sender_and_receiver: tuple[TCPSocket, TCPSocket]) -> None:
    sender, receiver = sender_and_receiver
    message = ESPChannelMessageJson(
        _type=MessageType.SIMULATION_STEP,
        _correlation_id=CORRELATION_ID,
        _payload="x" * LARGER_THAN_THE_SOCKET_BUFFERS,
    )

    sending = threading.Thread(target=sender.send, kwargs={"message": message})
    sending.start()
    received = receiver.receive()
    sending.join()

    assert received is not None
    assert received.to_esp_channel_message().payload() == message.payload()
