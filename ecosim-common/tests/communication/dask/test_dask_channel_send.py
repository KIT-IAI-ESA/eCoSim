from unittest.mock import MagicMock

import pytest

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel_message_json import ESPChannelMessageJson
from ecosim_common.communication.dask.dask_channel import DaskChannel
from ecosim_common.communication.message_type import MessageType
from ecosim_common.tech.parallel.parallel_event import ParallelEvent


def test_send_raises_when_the_message_cannot_be_delivered(monkeypatch: pytest.MonkeyPatch) -> None:
    peer_inbox = MagicMock()
    peer_inbox.put.side_effect = ConnectionError("scheduler is gone")
    monkeypatch.setattr(DaskChannel, "_peer_inbox", lambda _channel: peer_inbox)
    channel = DaskChannel(
        _connection_address=ConnectionAddress(ip="localhost", port=1),
        _is_finished=ParallelEvent.thread(),
        _is_listening=ParallelEvent.thread(),
        _closed=ParallelEvent.thread(),
        _connected=ParallelEvent.thread(init_set=True),
    )

    with pytest.raises(ConnectionError, match="scheduler is gone"):
        channel.send(ESPChannelMessageJson.empty(type=MessageType.PING))
