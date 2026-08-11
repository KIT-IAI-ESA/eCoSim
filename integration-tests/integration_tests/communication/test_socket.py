from queue import Queue

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_endpoint import ConnectionData
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.socket.endpoint_socket import EndpointSocket
from ecosim_common.communication.socket.socket_connector import SocketConnector
from integration_tests.communication.message_data_for_test import MessageDataForTest


def test_happy_path() -> None:
    server_address = ConnectionAddress(
        ip="localhost",
        port=1234,
    )
    endpoint_socket = EndpointSocket.for_connection_address(connection_address=server_address)
    endpoint_socket.listen_on_connection_loop_async(channel_handler=_mirror_message)
    endpoint_socket.is_listening_event().wait(timeout=10)

    socket_channel = SocketConnector().connect(connection_address=server_address)

    message_queue = Queue[ESPChannelMessage]()

    def handle_message(message: ESPChannelMessage) -> None:
        message_queue.put(message)

    socket_channel.listen_async(on_message=handle_message)
    socket_channel.is_listening_event().wait(timeout=1)

    correlation_id = CorrelationId.of_int(7777)
    data = MessageDataForTest(
        string="Test",
        integer=1111,
    )
    socket_channel.send(
        ESPChannelMessageJson.create(
            type=MessageType.CLIENT_META_DATA_REQUEST,
            correlation_id=correlation_id,
            payload=data,
        ),
    )

    received_data = message_queue.get()

    assert received_data.correlation_id() == correlation_id
    assert received_data.payload() == data.to_json()
    assert received_data.payload(MessageDataForTest) == data


def test_big_data() -> None:
    server_address = ConnectionAddress(
        ip="localhost",
        port=34567,
    )
    server_socket = EndpointSocket.for_connection_address(connection_address=server_address)
    server_socket.listen_on_connection_loop_async(channel_handler=_mirror_message)

    socket_channel = SocketConnector().connect(connection_address=server_address)

    message_queue = Queue[ESPChannelMessage]()

    def handle_message(message: ESPChannelMessage) -> None:
        message_queue.put(message)

    socket_channel.listen_async(on_message=handle_message)

    correlation_id = CorrelationId.of_int(7777)

    base_string = "hello world! "
    encoded_base_size = len(base_string.encode("utf-8"))
    mb_15 = 15 * 1024 * 1024  # 15MB = 15 * 1024 * 1024 bytes
    repetitions = mb_15 // encoded_base_size + 1
    final_string = base_string * repetitions
    final_size = len(final_string.encode("utf-8"))

    assert final_size > mb_15

    data = MessageDataForTest(
        string=final_string,
        integer=2222,
    )

    socket_channel.send(
        ESPChannelMessageJson.create(
            type=MessageType.CLIENT_META_DATA_REQUEST,
            correlation_id=correlation_id,
            payload=data,
        ),
    )

    received_data = message_queue.get()
    assert received_data.correlation_id() == correlation_id
    assert received_data.payload() == data.to_json()
    assert received_data.payload(MessageDataForTest) == data


def _mirror_message(connection_data: ConnectionData) -> None:
    data = connection_data.channel.listen_blocking()
    if not data:
        return
    connection_data.channel.send(data)
