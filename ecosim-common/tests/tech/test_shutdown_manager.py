import pickle
from dataclasses import dataclass, field
from typing import override

from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager


@dataclass
class CountingShutdownListener(ShutdownListener):
    notification_count: int = field(default=0)

    @override
    def on_app_shutdown(self) -> None:
        self.notification_count += 1


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
