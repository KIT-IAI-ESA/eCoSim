"""
The adding thread used to poll the queue with a 0.1s timeout. On a dask queue every empty poll raises
the 'TimeoutError' inside the scheduler process, which logs a full ERROR traceback for 'queue_get' -
10 tracebacks per second for as long as the queue is idle. So an idle thread must not poll at all.
"""

from __future__ import annotations

import time
from typing import override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.simulation.interface_value_history_thread import (
    InterfaceValueHistoryEntry,
    InterfaceValueHistoryThread,
)
from ecosim_test_common.test_data.generate_client_id import generate_random_client_id
from tests.simulation.history_test_setup import (
    RecordingRepositories,
    history,
    values,
)

_IDLE_IN_SECONDS = 1.0
# far below '_pop_timeout_in_seconds', so a passing test proves the wake up and not a short timeout
_WAKE_UP_LIMIT_IN_SECONDS = 5.0


class _CountingQueue(ESPQueue[InterfaceValueHistoryEntry]):
    """Counts how often the adding thread asks the queue for an entry."""

    def __init__(
        self,
        delegate: ESPQueue[InterfaceValueHistoryEntry],
    ) -> None:
        self._delegate = delegate
        self.pop_calls = 0

    @override
    def push(self, value: InterfaceValueHistoryEntry) -> None:
        self._delegate.push(value)

    @override
    def pop(self, timeout: float | None = None) -> InterfaceValueHistoryEntry:
        self.pop_calls += 1
        return self._delegate.pop(timeout=timeout)

    @override
    def pop_all(self) -> list[InterfaceValueHistoryEntry]:
        return self._delegate.pop_all()

    @override
    def qsize(self) -> int:
        return self._delegate.qsize()


def _counting_queue() -> _CountingQueue:
    return _CountingQueue(ESPQueue.of_type(ESPStructureType.THREAD))


def test_an_idle_thread_does_not_poll_the_queue() -> None:
    repositories = RecordingRepositories()
    queue = _counting_queue()
    value_history = history(
        repositories,
        entries_queue=queue,
        client_id=None,
    )
    try:
        time.sleep(_IDLE_IN_SECONDS)
        assert queue.pop_calls <= 1, "the adding thread polls the queue while it is idle"
    finally:
        value_history.close()


def test_flush_wakes_the_thread_instead_of_waiting_for_the_pop_timeout(
    communication_protocol: CommunicationProtocol,
) -> None:
    repositories = RecordingRepositories()
    client_id = generate_random_client_id()
    value_history = history(
        repositories,
        communication_protocol=communication_protocol,
        client_id=client_id,
    )

    value_history.add(time_step=0, client_id=client_id, interface_values=values())

    start = time.monotonic()
    value_history.flush()
    duration = time.monotonic() - start

    assert duration < _WAKE_UP_LIMIT_IN_SECONDS
    assert len(repositories.measurement_repository(client_id).all()) == 1
    value_history.close()


def test_close_wakes_the_thread_instead_of_waiting_for_the_pop_timeout(
    communication_protocol: CommunicationProtocol,
) -> None:
    repositories = RecordingRepositories()
    value_history = history(
        repositories,
        communication_protocol=communication_protocol,
        client_id=None,
    )

    start = time.monotonic()
    value_history.close()

    assert time.monotonic() - start < _WAKE_UP_LIMIT_IN_SECONDS


def test_waking_the_thread_adds_nothing_to_the_history(
    communication_protocol: CommunicationProtocol,
) -> None:
    """The wake up must never be mistaken for an entry."""
    repositories = RecordingRepositories()
    value_history = history(
        repositories,
        communication_protocol=communication_protocol,
        client_id=None,
    )

    value_history.flush()
    value_history.flush()
    value_history.close()

    assert repositories.measurement_repository(generate_random_client_id()).all() == []
    assert value_history._entries.keys() == set()  # noqa: SLF001


def test_the_pop_timeout_is_long_enough_to_not_flood_the_scheduler() -> None:
    assert InterfaceValueHistoryThread._pop_timeout_in_seconds >= 60.0  # noqa: SLF001
