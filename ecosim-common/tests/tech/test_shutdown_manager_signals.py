import signal
import threading
from dataclasses import dataclass, field
from typing import override

import pytest

from ecosim_common.tech import shutdown_manager
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from tests.tech.shutdown_listeners import CountingShutdownListener, RaisingShutdownListener

SIGNALS_AND_EXIT_CODES = [(signal.SIGINT, 333), (signal.SIGTERM, 444)]


@dataclass
class SignalledShutdownListener(ShutdownListener):
    finished: bool = field(default=False)

    @override
    def on_app_shutdown(self) -> None:
        signal.raise_signal(signal.SIGTERM)
        self.finished = True


class SignalledWhileSettingEvent(threading.Event):
    @override
    def set(self) -> None:
        signal.raise_signal(signal.SIGTERM)
        super().set()


@pytest.fixture
def no_signal_grace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutdown_manager, "SIGNAL_GRACE_IN_SECONDS", 0)


@pytest.mark.parametrize(("signal_number", "exit_code"), SIGNALS_AND_EXIT_CODES)
def test_signal_notifies_the_listeners_and_exits(signal_number: signal.Signals, exit_code: int) -> None:
    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal_number)

    assert exit_info.value.code == exit_code
    assert listener.notification_count == 1


def test_signal_exits_even_if_a_listener_raises() -> None:
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(RaisingShutdownListener())
    ShutdownManager().register_listener(later_listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGTERM)

    assert exit_info.value.code == 444
    assert later_listener.notification_count == 1


def test_second_signal_right_after_the_first_does_not_interrupt_the_shutdown() -> None:
    signalled_listener = SignalledShutdownListener()
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(signalled_listener)
    ShutdownManager().register_listener(later_listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGINT)

    assert exit_info.value.code == 333
    assert signalled_listener.finished
    assert later_listener.notification_count == 1


def test_signal_during_the_shutdown_at_application_end_does_not_interrupt_it() -> None:
    signalled_listener = SignalledShutdownListener()
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(signalled_listener)
    ShutdownManager().register_listener(later_listener)

    ShutdownManager().set_shutdown_at_application_end()

    assert signalled_listener.finished
    assert later_listener.notification_count == 1


def test_signal_while_the_shutdown_sets_the_event_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ShutdownManager(), "shutdown_event", SignalledWhileSettingEvent())
    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    ShutdownManager().set_shutdown_at_application_end()

    assert listener.notification_count == 1


def test_copy_of_a_signal_after_the_grace_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [0.0]

    class LateSignalledShutdownListener(ShutdownListener):
        @override
        def on_app_shutdown(self) -> None:
            clock[0] += shutdown_manager.SIGNAL_GRACE_IN_SECONDS + 1
            signal.raise_signal(signal.SIGTERM)

    monkeypatch.setattr(shutdown_manager.time, "monotonic", lambda: clock[0])
    copy_receiving_listener = SignalledShutdownListener()
    ShutdownManager().register_listener(LateSignalledShutdownListener())
    ShutdownManager().register_listener(copy_receiving_listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGINT)

    assert exit_info.value.code == 333
    assert copy_receiving_listener.finished


@pytest.mark.usefixtures("no_signal_grace")
@pytest.mark.parametrize(("signal_number", "exit_code"), SIGNALS_AND_EXIT_CODES)
def test_signal_exits_after_the_grace(signal_number: signal.Signals, exit_code: int) -> None:
    ShutdownManager().set_shutdown_at_application_end()

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal_number)

    assert exit_info.value.code == exit_code


@pytest.mark.usefixtures("no_signal_grace")
def test_signal_after_the_grace_interrupts_a_listener_and_the_later_ones_still_run() -> None:
    signalled_listener = SignalledShutdownListener()
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(signalled_listener)
    ShutdownManager().register_listener(later_listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGINT)

    assert exit_info.value.code == 333
    assert not signalled_listener.finished
    assert later_listener.notification_count == 1
