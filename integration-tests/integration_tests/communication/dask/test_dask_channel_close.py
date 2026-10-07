import threading

import dask.distributed as dd
import pytest
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.channel.esp_channel import ConnectionData
from ecosim_common.communication.dask.channel_endpoint import ChannelEndpoint
from ecosim_common.communication.dask.dask_channel import DaskChannel, create_internal_dask_id
from ecosim_common.tech.parallel.parallel_event import ParallelEvent

_ADDRESS = ConnectionAddress(ip="localhost", port=8786)
_RECEIVE_TIMEOUT_IN_SECONDS = 30
_WAKE_UP_TIMEOUT_IN_SECONDS = 10.0


def _ignore_connection(connection_data: ConnectionData) -> None:
    """The accept loop runs on a worker, so its handler must be picklable - no test here connects."""


def _connected_end(endpoint: ChannelEndpoint, dask_id: str) -> DaskChannel:
    return DaskChannel(
        _connection_address=_ADDRESS,
        _internal_dask_id=dask_id,
        _connected=ParallelEvent.dask(init_set=True),
        _endpoint=endpoint,
    )


def _listening_channel() -> DaskChannel:
    channel = DaskChannel.of(_ADDRESS)
    channel.listen_on_connection_loop_async(channel_handler=_ignore_connection)
    return channel


def _receive_returns_in_time(channel: DaskChannel) -> bool:
    receiver = threading.Thread(target=channel.listen_blocking, args=(_RECEIVE_TIMEOUT_IN_SECONDS,), daemon=True)
    receiver.start()
    receiver.join(timeout=_WAKE_UP_TIMEOUT_IN_SECONDS)
    return not receiver.is_alive()


@pytest.mark.parametrize("endpoint", [ChannelEndpoint.CONNECTOR, ChannelEndpoint.LISTENER])
def test_closing_a_connection_keeps_the_accept_loop_running(dask_client: dd.Client, endpoint: ChannelEndpoint) -> None:
    """Every channel shares the one cluster wide accept loop - one client hanging up must not end it for all."""
    listener = _listening_channel()

    _connected_end(endpoint, create_internal_dask_id()).close()

    assert listener.is_listening_on_connection_event().is_set()


def test_closing_the_listening_channel_stops_the_accept_loop(dask_client: dd.Client) -> None:
    listener = _listening_channel()

    listener.close()

    assert not listener.is_listening_on_connection_event().is_set()


def test_closing_a_connection_tells_the_peer_and_wakes_the_own_reader(dask_client: dd.Client) -> None:
    dask_id = create_internal_dask_id()
    connector = _connected_end(ChannelEndpoint.CONNECTOR, dask_id)
    peer = _connected_end(ChannelEndpoint.LISTENER, dask_id)

    connector.close()

    assert _receive_returns_in_time(peer), "the peer was not told that the connection closed"
    assert _receive_returns_in_time(connector), "the own reader was not woken up"


def test_a_refused_listener_does_not_stop_the_running_accept_loop(dask_client: dd.Client) -> None:
    """'start_listening' refuses while another channel listens - that other channel owns the loop."""
    owner = _listening_channel()
    refused = _listening_channel()

    refused.close()

    assert owner.is_listening_on_connection_event().is_set()
