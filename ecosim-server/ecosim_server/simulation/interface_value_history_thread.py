from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import List, Tuple

from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_queue import ESPQueue
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories

DEFAULT_VALUES_MARKER = -1

InterfaceValueHistoryEntries = ESPMap[int, dict[ClientID, List[ProtocolInterfaceValue]]]


@dataclass(frozen=True)
class InterfaceValueHistoryEntry:
    time_step: int
    client_id: ClientID
    interface_values: Tuple[ProtocolInterfaceValue, ...]


def add_to_entries(
    entries: InterfaceValueHistoryEntries,
    entry: InterfaceValueHistoryEntry,
) -> None:
    with entries.transaction() as current_entries:
        if entry.time_step not in current_entries:
            current_entries[entry.time_step] = {}
        if entry.client_id not in current_entries[entry.time_step]:
            current_entries[entry.time_step][entry.client_id] = []
        current_entries[entry.time_step][entry.client_id].extend(entry.interface_values)


@dataclass
class InterfaceValueHistoryThread:
    """
    Pops the entries of the 'InterfaceValueHistory' and adds them to the entries and to the repositories - so
    the caller of 'InterfaceValueHistory.add' does not wait for the (slow) repository write. There is only one
    thread, so the entries are added in the order they were pushed in.

    ATTENTION: an entry is added some time after it was pushed - so call 'flush' before reading the entries or
               the repositories, and 'close' when nothing is pushed anymore.
    """

    logger = ESPLogger("InterfaceValueHistoryThread")

    THREAD_NAME = "InterfaceValueHistoryAdder"

    _pop_timeout_in_seconds = 0.1
    _join_timeout_in_seconds = 5.0

    _entries_queue: ESPQueue[InterfaceValueHistoryEntry] = field()
    _entries: InterfaceValueHistoryEntries = field()
    _repositories: Repositories = field()
    _simulation_config: SimulationConfig = field()
    _condition: threading.Condition = field(init=False, default_factory=threading.Condition)
    _thread: threading.Thread | None = field(init=False, default=None)
    _flush_requested: bool = field(init=False, default=False)
    _first_failure: BaseException | None = field(init=False, default=None)

    def start(self) -> None:
        InterfaceValueHistoryThread.logger.debug("Starting the adding thread")
        self._thread = threading.Thread(
            target=self._add_until_stopped,
            name=InterfaceValueHistoryThread.THREAD_NAME,
            daemon=True,
        )
        self._thread.start()

    def flush(self) -> None:
        """Waits until the thread found nothing left to add. Raises if an entry could not be added."""
        with self._condition:
            if self._thread is not None:
                self._flush_requested = True
                self._condition.wait_for(lambda: not self._flush_requested)
            failure = self._first_failure
            self._first_failure = None
        if failure is not None:
            raise RuntimeError("Failed to add at least one entry to the history.") from failure

    def close(self) -> None:
        """Adds the remaining entries and stops the thread."""
        try:
            self.flush()
        finally:
            self._stop()

    def _stop(self) -> None:
        thread = self._thread
        self._thread = None  # the thread ends its loop as soon as it is not the current thread anymore
        if thread is None:
            return
        InterfaceValueHistoryThread.logger.debug("Stopping the adding thread")
        thread.join(timeout=InterfaceValueHistoryThread._pop_timeout_in_seconds + InterfaceValueHistoryThread._join_timeout_in_seconds)
        if thread.is_alive():
            InterfaceValueHistoryThread.logger.error("The adding thread did not stop in time.")

    def _add_until_stopped(self) -> None:
        while threading.current_thread() is self._thread:
            entry = self._entries_queue.pop_or_none(timeout=InterfaceValueHistoryThread._pop_timeout_in_seconds)
            if entry is None:
                self._report_nothing_left_to_add()
                continue
            self._add(entry)

    def _report_nothing_left_to_add(self) -> None:
        """A 'flush' returns as soon as the thread popped an empty queue - then everything pushed before is added."""
        with self._condition:
            self._flush_requested = False
            self._condition.notify_all()

    def _add(self, entry: InterfaceValueHistoryEntry) -> None:
        """Runs in the adding thread - so it must not let an exception escape."""
        try:
            add_to_entries(self._entries, entry)
            self._add_to_repository(entry)
            InterfaceValueHistoryThread.logger.debug("Adding new entry: %s ... done.", entry)
        except Exception as error:  # one failed entry must not kill the adding thread
            InterfaceValueHistoryThread.logger.error("Adding new entry %s failed: %s", entry, error)
            self._remember_failure(error)

    def _add_to_repository(self, entry: InterfaceValueHistoryEntry) -> None:
        if entry.time_step == DEFAULT_VALUES_MARKER:
            return
        self._repositories.measurement_repository(entry.client_id).add(
            values=entry.interface_values,
            timestamp=self._simulation_config.date_time_for_step(entry.time_step),
        )

    def _remember_failure(self, error: BaseException) -> None:
        with self._condition:
            if self._first_failure is None:
                self._first_failure = error
