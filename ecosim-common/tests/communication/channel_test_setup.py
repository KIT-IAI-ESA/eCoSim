import queue
import threading

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.dask.channel_endpoint import ChannelEndpoint
from ecosim_common.communication.dask.dask_channel import DaskChannel, create_internal_dask_id
from ecosim_common.communication.message_type import MessageType
from ecosim_common.tech.parallel.parallel_event import ParallelEvent

ADDRESS = ConnectionAddress(ip="127.0.0.1", port=1234)
SHORT_TIMEOUT_IN_SECONDS = 1
BOUND_IN_SECONDS = 15


def simple_message() -> ESPChannelMessage:
    return ESPChannelMessageJson.empty(type=MessageType.SIMULATION_STEP)


def listen_blocking_bounded(channel: ESPChannel, timeout_in_seconds: int | None = None) -> ESPChannelMessage | None:
    outcome: queue.Queue[ESPChannelMessage | Exception | None] = queue.Queue()
    threading.Thread(target=_listen_into, args=(outcome, channel, timeout_in_seconds), daemon=True).start()
    # a hang raises queue.Empty, which pytest.raises(TimeoutError) does not accept
    result = outcome.get(timeout=BOUND_IN_SECONDS)
    if isinstance(result, Exception):
        raise result
    return result


def _listen_into(outcome: queue.Queue[ESPChannelMessage | Exception | None], channel: ESPChannel, timeout_in_seconds: int | None) -> None:
    try:
        outcome.put(channel.listen_blocking(timeout_in_seconds=timeout_in_seconds))
    except Exception as error:
        outcome.put(error)


def dask_channel_pair() -> tuple[DaskChannel, DaskChannel]:
    dask_id = create_internal_dask_id()
    return _dask_end(endpoint=ChannelEndpoint.CONNECTOR, dask_id=dask_id), _dask_end(endpoint=ChannelEndpoint.LISTENER, dask_id=dask_id)


def _dask_end(endpoint: ChannelEndpoint, dask_id: str) -> DaskChannel:
    return DaskChannel(
        _connection_address=ADDRESS,
        _internal_dask_id=dask_id,
        _connected=ParallelEvent.dask(init_set=True),
        _endpoint=endpoint,
    )
