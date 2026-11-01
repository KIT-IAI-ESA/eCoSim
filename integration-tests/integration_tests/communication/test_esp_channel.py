import threading

from integration_tests.communication.message_data_for_test import MessageDataForTest
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ConnectionData
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.message_type import MessageType
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.structures.esp_queue import ESPQueue

_MESSAGE_COUNT = 20


def test_happy_path(communication_protocol: CommunicationProtocol) -> None:
    server_address = ConnectionAddress(
        ip="localhost",
        port=get_free_port(),
    )
    connector = ESPChannelConnector(communication_protocol)
    listening_channel = connector.listener(server_address)
    listening_channel.listen_on_connection_loop_async(channel_handler=_mirror_message)
    assert listening_channel.is_listening_on_connection_event().wait(timeout=10)

    socket_channel = connector.connect(connection_address=server_address)

    message_queue: ESPQueue[ESPChannelMessage] = ESPQueue.of_communication_protocol(communication_protocol)

    def handle_message(message: ESPChannelMessage) -> None:
        message_queue.push(message)

    socket_channel.listen_on_message_async(on_message=handle_message)
    assert socket_channel.is_listening_event().wait(timeout=10)

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

    received_data = message_queue.pop(timeout=30)

    assert received_data.correlation_id() == correlation_id
    assert received_data.payload() == data.to_json()
    assert received_data.payload(MessageDataForTest) == data


def test_big_data(communication_protocol: CommunicationProtocol) -> None:
    server_address = ConnectionAddress(
        ip="localhost",
        port=get_free_port(),
    )
    connector = ESPChannelConnector(communication_protocol)
    listening_channel = connector.listener(server_address)
    listening_channel.listen_on_connection_loop_async(channel_handler=_mirror_message)
    assert listening_channel.is_listening_on_connection_event().wait(timeout=10)

    socket_channel = connector.connect(connection_address=server_address)

    message_queue: ESPQueue[ESPChannelMessage] = ESPQueue.of_communication_protocol(communication_protocol)

    def handle_message(message: ESPChannelMessage) -> None:
        message_queue.push(message)

    socket_channel.listen_on_message_async(on_message=handle_message)

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

    received_data = message_queue.pop(timeout=30)
    assert received_data.correlation_id() == correlation_id
    assert received_data.payload() == data.to_json()
    assert received_data.payload(MessageDataForTest) == data


def test_message_handler_stays_in_the_calling_process(communication_protocol: CommunicationProtocol) -> None:
    """
    The handler given to 'listen_on_message_async' must run in the process that registered it.

    It may close over process-local resources that cannot be pickled - an FMU's ctypes handle, a Matlab
    engine, a Pyro5 proxy. Appending to a plain local list also proves the handler did not run on a copy
    of itself elsewhere: a remote copy would leave this list empty.
    """
    server_address = ConnectionAddress(
        ip="localhost",
        port=get_free_port(),
    )
    connector = ESPChannelConnector(communication_protocol)
    listening_channel = connector.listener(server_address)
    listening_channel.listen_on_connection_loop_async(channel_handler=_mirror_message)
    assert listening_channel.is_listening_on_connection_event().wait(timeout=10)

    channel = connector.connect(connection_address=server_address)

    process_local_resource = threading.Lock()  # stands in for a native handle - not picklable
    received_in_this_process: list[ESPChannelMessage] = []
    message_received = threading.Event()

    def handle_message(message: ESPChannelMessage) -> None:
        with process_local_resource:
            received_in_this_process.append(message)
        message_received.set()

    channel.listen_on_message_async(on_message=handle_message)
    assert channel.is_listening_event().wait(timeout=10)

    correlation_id = CorrelationId.of_int(4242)
    data = MessageDataForTest(
        string="process local",
        integer=42,
    )
    channel.send(
        ESPChannelMessageJson.create(
            type=MessageType.CLIENT_META_DATA_REQUEST,
            correlation_id=correlation_id,
            payload=data,
        ),
    )

    assert message_received.wait(timeout=30)
    assert len(received_in_this_process) == 1
    assert received_in_this_process[0].correlation_id() == correlation_id
    assert received_in_this_process[0].payload(MessageDataForTest) == data


def test_message_order_is_kept(communication_protocol: CommunicationProtocol) -> None:
    """A channel is a stream: what one side sends first has to arrive first."""
    server_address = ConnectionAddress(
        ip="localhost",
        port=get_free_port(),
    )
    connector = ESPChannelConnector(communication_protocol)
    listening_channel = connector.listener(server_address)
    listening_channel.listen_on_connection_loop_async(channel_handler=_mirror_messages)
    assert listening_channel.is_listening_on_connection_event().wait(timeout=10)

    channel = connector.connect(connection_address=server_address)

    message_queue: ESPQueue[ESPChannelMessage] = ESPQueue.of_communication_protocol(communication_protocol)
    channel.listen_on_message_async(on_message=message_queue.push)
    assert channel.is_listening_event().wait(timeout=10)

    for step in range(_MESSAGE_COUNT):
        channel.send(
            ESPChannelMessageJson.create(
                type=MessageType.CLIENT_META_DATA_REQUEST,
                correlation_id=CorrelationId.of_int(step),
                payload=MessageDataForTest(string="order", integer=step),
            ),
        )

    received_ids = [message_queue.pop(timeout=30).correlation_id() for _ in range(_MESSAGE_COUNT)]
    assert received_ids == [CorrelationId.of_int(step) for step in range(_MESSAGE_COUNT)]


def _mirror_message(connection_data: ConnectionData) -> None:
    data = connection_data.channel.listen_blocking()
    if not data:
        return
    connection_data.channel.send(data)


def _mirror_messages(connection_data: ConnectionData) -> None:
    """Mirrors until the peer hangs up - 'listen_blocking' returns None."""
    while True:
        data = connection_data.channel.listen_blocking()
        if not data:
            return
        connection_data.channel.send(data)
