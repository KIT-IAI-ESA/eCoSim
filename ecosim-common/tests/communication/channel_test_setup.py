import threading
import time
from dataclasses import dataclass, field
from typing import ClassVar, override

import dask.distributed as distributed

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ESPChannel
from ecosim_common.communication.channel.esp_channel_message import ESPChannelMessage
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.dask.channel_endpoint import ChannelEndpoint
from ecosim_common.communication.dask.dask_channel import DaskChannel, create_internal_dask_id
from ecosim_common.communication.message_type import MessageType
from ecosim_common.tech.parallel.parallel_event import ParallelEvent

ADDRESS = ConnectionAddress(ip="127.0.0.1", port=1234)


@dataclass
class RaisingMessageHandler:
    ERROR_MESSAGE: ClassVar[str] = "the handler failed"

    call_count: int = field(default=0)

    def __call__(self, message: ESPChannelMessage) -> None:
        self.call_count += 1
        raise RuntimeError(RaisingMessageHandler.ERROR_MESSAGE)


@dataclass
class SlowEchoHandler:
    channel: ESPChannel
    delay_in_seconds: int

    def __call__(self, message: ESPChannelMessage) -> None:
        time.sleep(self.delay_in_seconds)
        self.channel.send(message)


@dataclass(frozen=True)
class LostSchedulerEvent(ParallelEvent):
    @override
    def _event(self) -> threading.Event | distributed.Event:
        raise OSError("the Dask scheduler is lost")


def simple_message() -> ESPChannelMessage:
    return ESPChannelMessageJson.empty(type=MessageType.SIMULATION_STEP)


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
