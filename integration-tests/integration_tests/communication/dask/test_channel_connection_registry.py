import time
from unittest.mock import MagicMock

import dask.distributed as dd
from ecosim_common.communication.dask.channel_connection_registry import ChannelConnectionRegistry


def _wait_until_queue_is_empty(registry: ChannelConnectionRegistry) -> None:
    deadline = time.monotonic() + 10
    while registry._connection_queue.qsize() > 0:  # noqa: SLF001
        assert time.monotonic() < deadline, "the accept loop did not consume the sentinel"
        time.sleep(0.1)


def test_stopping_ends_the_running_loop_and_a_new_one_can_start(dask_client: dd.Client) -> None:
    registry = ChannelConnectionRegistry.of(dask_client)
    assert registry.start_listening(MagicMock()) is True

    registry.stop_listening()
    _wait_until_queue_is_empty(registry)

    assert registry.start_listening(MagicMock()) is True


def test_starting_a_running_registry_is_not_possible(dask_client: dd.Client) -> None:
    registry = ChannelConnectionRegistry.of(dask_client)
    assert registry.start_listening(MagicMock()) is True
    _wait_until_queue_is_empty(registry)
    assert registry.start_listening(MagicMock()) is False


def test_stopping_twice_queues_only_one_sentinel(dask_client: dd.Client) -> None:
    registry = ChannelConnectionRegistry.of(dask_client)
    registry.start_listening(MagicMock())
    registry.is_listening_event().wait(2)

    registry.stop_listening()
    registry.stop_listening()

    assert registry._connection_queue.pop_all() == [registry._closed_sentinel]  # noqa: SLF001


def test_stopping_ten_times_queues_only_one_sentinel(dask_client: dd.Client) -> None:
    registry = ChannelConnectionRegistry.of(dask_client)
    registry.start_listening(MagicMock())
    registry.is_listening_event().wait(2)

    for _ in [0 - 9]:
        registry.stop_listening()

    assert registry._connection_queue.pop_all() == [registry._closed_sentinel]  # noqa: SLF001


def test_closing_after_the_dask_client_is_gone_does_nothing(dask_client: dd.Client) -> None:
    """Another shutdown listener may close the dask client first - its events cannot be reached any more."""
    registry = ChannelConnectionRegistry.of(dask_client)
    registry.is_listening_event().set()
    dask_client.close()

    registry.close()
