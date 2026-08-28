import pickle

import dask.distributed as dd
import distributed
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_connector import ESPChannelConnector
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.correlation_id import CorrelationId
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.communication.message_type import MessageType
from integration_tests.communication.message_data_for_test import MessageDataForTest

_SEND_COUNT = 5


def test_sending_reuses_one_queue_handle(dask_client: dd.Client) -> None:
    """
    'distributed.Queue.__init__' is a blocking 'queue_create' on the scheduler.

    Constructing a handle per send therefore costs a second round trip on top of the 'put' itself, so
    the handle is created once and kept - the same reason 'DaskESPQueue' caches its queue.
    """
    channel = _connected_channel()
    created_queues: list[str] = []
    original_init = distributed.Queue.__init__

    def counting_init(queue: distributed.Queue, *args: object, **kwargs: object) -> None:
        original_init(queue, *args, **kwargs)  # type: ignore[arg-type]
        created_queues.append(str(queue.name))

    distributed.Queue.__init__ = counting_init  # type: ignore[method-assign]
    try:
        for step in range(_SEND_COUNT):
            channel.send(_message(step))
    finally:
        distributed.Queue.__init__ = original_init  # type: ignore[method-assign]

    assert len(created_queues) == 1, f"expected one queue handle for {_SEND_COUNT} sends, got {created_queues}"


def test_a_pickled_channel_carries_no_queue_handle(dask_client: dd.Client) -> None:
    """The channel travels to a worker, where a cached handle would be rebuilt - i.e. a round trip per unpickling."""
    channel = _connected_channel()
    channel.send(_message(1))  # fills the cache

    unpickled: DaskChannel = pickle.loads(pickle.dumps(channel))

    assert unpickled.__getstate__()["_peer_inbox_queue"] is None
    assert unpickled.__getstate__()["_inbox_queue"] is None


def _connected_channel() -> DaskChannel:
    channel = ESPChannelConnector(CommunicationProtocol.DASK).connect(
        connection_address=ConnectionAddress(ip="localhost", port=8786),
    )
    assert isinstance(channel, DaskChannel)
    return channel


def _message(step: int) -> ESPChannelMessageJson:
    return ESPChannelMessageJson.create(
        type=MessageType.CLIENT_META_DATA_REQUEST,
        correlation_id=CorrelationId.of_int(step),
        payload=MessageDataForTest(string="handle", integer=step),
    )
