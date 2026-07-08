import dask.distributed as dd

from ecosim_common.communication.channel.esp_channel_endpoint import ConnectionData
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.channel.connection_address import ConnectionAddress

from ecosim_common.communication.message_type import MessageType
from ecosim_common.communication.dask.endpoint_dask import EndpointDask
from ecosim_common.communication.dask.dask_connector import DaskConnector
from integration_tests.communication.message_data_for_test import MessageDataForTest


def clear_datasets(client: dd.Client) -> None:
    for key in client.list_datasets():
        client.unpublish_dataset(key)


def test_happy_path(dask_client: dd.Client) -> None:
    server_address = ConnectionAddress.of_dask_client(dask_client)
    server_dask_client = EndpointDask(_connection_address=server_address)
    server_dask_client.listen_async(on_new_channel=_mirror_message)

    dask_client_channel = DaskConnector().connect(connection_address=server_address)

    message_queue = dd.Queue()

    def handle_message(message: ESPChannelMessage) -> None:
        message_queue.put(message)

    dask_client_channel.listen_async(on_message=handle_message)

    correlation_id = CorrelationId.of_int(7777)
    data = MessageDataForTest(
        string="Test",
        integer=1111,
    )
    dask_client_channel.send(
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


def test_big_data(dask_client: dd.Client) -> None:
    server_address = ConnectionAddress.of_dask_client(dask_client)
    server_dask_client = EndpointDask(_connection_address=server_address)
    server_dask_client.listen_async(on_new_channel=_mirror_message)

    dask_client_channel = DaskConnector().connect(connection_address=server_address)

    message_queue = dd.Queue()

    def handle_message(message: ESPChannelMessage) -> None:
        message_queue.put(message)

    dask_client_channel.listen_async(on_message=handle_message)

    correlation_id = CorrelationId.of_int(7777)

    base_string = "hello world! "
    encoded_base_size = len(base_string.encode('utf-8'))
    mb_15 = 15 * 1024 * 1024
    repetitions = mb_15 // encoded_base_size + 1
    final_string = base_string*repetitions
    final_size = len(final_string.encode('utf-8'))

    assert final_size > mb_15

    data = MessageDataForTest(
        string=final_string,
        integer=2222,
    )
    dask_client_channel.send(
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
