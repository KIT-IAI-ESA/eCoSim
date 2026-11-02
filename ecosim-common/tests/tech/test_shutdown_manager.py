import pickle

import pytest

from ecosim_common.tech.shutdown_manager import ShutdownManager
from tests.tech.shutdown_listeners import CountingShutdownListener, OrderRecordingShutdownListener, RaisingShutdownListener


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


def test_listeners_are_notified_in_the_order_of_registration() -> None:
    notified_names: list[str] = []
    for name in ("first", "second", "third"):
        ShutdownManager().register_listener(OrderRecordingShutdownListener(name=name, notified_names=notified_names))

    ShutdownManager().set_shutdown_at_application_end()

    assert notified_names == ["first", "second", "third"]


def test_shutdown_starting_while_a_listener_registers_notifies_it_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    'register_listener' adds the listener and then checks the event.

    The hook starts the shutdown between the two, as another thread could, so both try to notify the listener.
    """
    manager = ShutdownManager()
    listener = CountingShutdownListener()
    original_is_set = manager.shutdown_event.is_set

    def start_shutdown_then_check() -> bool:
        monkeypatch.setattr(manager.shutdown_event, "is_set", original_is_set)
        manager.set_shutdown_at_application_end()
        return original_is_set()

    monkeypatch.setattr(manager.shutdown_event, "is_set", start_shutdown_then_check)

    manager.register_listener(listener)

    assert listener.notification_count == 1


def test_raising_listener_does_not_stop_the_later_ones() -> None:
    raising_listener = RaisingShutdownListener()
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(raising_listener)
    ShutdownManager().register_listener(later_listener)

    ShutdownManager().set_shutdown_at_application_end()

    assert raising_listener.notified
    assert id(raising_listener) not in ShutdownManager._listener  # noqa: SLF001
    assert later_listener.notification_count == 1


def test_exception_of_a_listener_registered_after_shutdown_is_caught() -> None:
    ShutdownManager().set_shutdown_at_application_end()
    listener = RaisingShutdownListener()

    ShutdownManager().register_listener(listener)

    assert listener.notified


def test_manager_is_shared_only_when_it_is_complete(monkeypatch: pytest.MonkeyPatch) -> None:
    """Another thread getting a half-built instance would find no 'shutdown_event'."""
    ShutdownManager.reset_instance()
    instances_during_creation: list[ShutdownManager | None] = []

    def record_the_instance_and_find_no_client() -> None:
        instances_during_creation.append(ShutdownManager._instance)  # noqa: SLF001
        raise ValueError("no dask client")

    monkeypatch.setattr("dask.distributed.get_client", record_the_instance_and_find_no_client)

    ShutdownManager()

    assert instances_during_creation == [None]


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
