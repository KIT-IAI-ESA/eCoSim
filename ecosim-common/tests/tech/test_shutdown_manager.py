import pickle
import threading
from typing import override

import pytest

from ecosim_common.tech.shutdown_manager import ShutdownManager
from tests.tech.shutdown_listeners import CountingShutdownListener, RaisingShutdownListener


class ShutdownStartingAtFirstCheckEvent(threading.Event):
    _checked: bool = False

    @override
    def is_set(self) -> bool:
        if not self._checked:
            self._checked = True
            ShutdownManager().set_shutdown_at_application_end()
        return super().is_set()


def test_listener_is_notified_on_shutdown() -> None:
    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    ShutdownManager().set_shutdown_at_application_end()

    assert listener.notification_count == 1
    assert ShutdownManager().is_shutdown()


def test_listener_is_notified_only_once_on_repeated_shutdown() -> None:
    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    ShutdownManager().set_shutdown_at_application_end()
    ShutdownManager().set_shutdown_at_application_end()

    assert listener.notification_count == 1


def test_listener_registered_after_shutdown_is_notified_immediately() -> None:
    ShutdownManager().set_shutdown_at_application_end()

    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    assert listener.notification_count == 1


def test_listener_registering_while_a_shutdown_starts_is_notified_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ShutdownManager(), "shutdown_event", ShutdownStartingAtFirstCheckEvent())
    listener = CountingShutdownListener()

    ShutdownManager().register_listener(listener)

    assert listener.notification_count == 1


def test_raising_listener_does_not_stop_the_later_ones(caplog: pytest.LogCaptureFixture) -> None:
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(RaisingShutdownListener())
    ShutdownManager().register_listener(later_listener)

    ShutdownManager().set_shutdown_at_application_end()

    assert later_listener.notification_count == 1
    assert "Shutdown listener RaisingShutdownListener failed" in caplog.text
    assert "RuntimeError: listener failed" in caplog.text


def test_raising_listener_registered_after_shutdown_does_not_raise() -> None:
    ShutdownManager().set_shutdown_at_application_end()

    ShutdownManager().register_listener(RaisingShutdownListener())


def test_thread_using_the_manager_while_it_is_created_waits_for_it(monkeypatch: pytest.MonkeyPatch) -> None:
    ShutdownManager.reset_instance()
    errors: list[Exception] = []

    def register_listener() -> None:
        try:
            ShutdownManager().register_listener(CountingShutdownListener())
        except Exception as e:
            errors.append(e)

    other_thread = threading.Thread(target=register_listener)

    def get_client_while_the_other_thread_runs() -> None:
        other_thread.start()
        other_thread.join(timeout=0.2)
        raise ValueError("no dask client")

    monkeypatch.setattr("dask.distributed.get_client", get_client_while_the_other_thread_runs)

    ShutdownManager()
    other_thread.join()

    assert errors == []


def test_manager_pickles_as_the_singleton_of_the_receiving_process() -> None:
    """A copy would shut down itself instead of the process it was sent to - and would not even pickle."""
    restored = pickle.loads(pickle.dumps(ShutdownManager()))

    # assert with 'is' (instead of '==') compares the identity - which is what we want here -> the identity must be the same (and not a copy)
    assert restored is ShutdownManager()


def test_manager_pickles_as_the_singleton_of_the_receiving_process_by_method() -> None:
    """A copy would shut down itself instead of the process it was sent to - and would not even pickle."""
    restored = pickle.loads(pickle.dumps(ShutdownManager().set_shutdown_at_application_end))

    # assert with 'is' (instead of '==') compares the identity - which is what we want here -> the identity must be the same (and not a copy)
    assert restored.__self__ is ShutdownManager()
