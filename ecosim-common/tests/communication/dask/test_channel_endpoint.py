from ecosim_common.communication.dask.channel_endpoint import ChannelEndpoint

_DASK_ID = "4f1c"


def test_peer_of_listener_is_the_connector() -> None:
    assert ChannelEndpoint.LISTENER.peer() == ChannelEndpoint.CONNECTOR


def test_peer_of_connector_is_the_listener() -> None:
    assert ChannelEndpoint.CONNECTOR.peer() == ChannelEndpoint.LISTENER


def test_every_endpoint_owns_its_own_inbox() -> None:
    """The name is a cluster wide key, so it has to name the owner - a relative 'my inbox' would collide."""
    assert ChannelEndpoint.LISTENER.inbox_name(_DASK_ID) != ChannelEndpoint.CONNECTOR.inbox_name(_DASK_ID)


def test_both_endpoints_agree_on_the_name_of_an_inbox() -> None:
    assert ChannelEndpoint.CONNECTOR.peer().inbox_name(_DASK_ID) == ChannelEndpoint.LISTENER.inbox_name(_DASK_ID)


def test_inbox_name_contains_the_connection_id() -> None:
    assert ChannelEndpoint.LISTENER.inbox_name(_DASK_ID) == f"{_DASK_ID}-listener-inbox"
    assert ChannelEndpoint.CONNECTOR.inbox_name(_DASK_ID) == f"{_DASK_ID}-connector-inbox"
