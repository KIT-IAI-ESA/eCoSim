import signal
import threading
from typing import override

import pytest

from ecosim_common.tech import shutdown_manager
from ecosim_common.tech.shutdown_manager import ShutdownManager
from tests.tech.shutdown_listeners import (
    CountingShutdownListener,
    GraceEndingSignalRaisingShutdownListener,
    RaisingShutdownListener,
    SignalRaisingShutdownListener,
)

SIGNALS_AND_EXIT_CODES = [
    (signal.SIGINT, ShutdownManager.INTERRUPT_EXIT_CODE),
    (signal.SIGTERM, ShutdownManager.TERMINATE_EXIT_CODE),
]


class SignalRaisingWhileSettingEvent(threading.Event):
    @override
    def set(self) -> None:
        signal.raise_signal(signal.SIGTERM)
        super().set()


@pytest.fixture(autouse=True)
def auto_initialize_shutdown_manager() -> None:
    ShutdownManager().init()


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

    assert exit_info.value.code == ShutdownManager.TERMINATE_EXIT_CODE
    assert later_listener.notification_count == 1


def test_second_signal_right_after_the_first_does_not_interrupt_the_shutdown() -> None:
    signal_raising_listener = SignalRaisingShutdownListener()
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(signal_raising_listener)
    ShutdownManager().register_listener(later_listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGINT)

    assert exit_info.value.code == ShutdownManager.INTERRUPT_EXIT_CODE
    assert signal_raising_listener.finished
    assert later_listener.notification_count == 1


def test_signal_during_the_shutdown_at_application_end_does_not_interrupt_it() -> None:
    signal_raising_listener = SignalRaisingShutdownListener()
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(signal_raising_listener)
    ShutdownManager().register_listener(later_listener)

    ShutdownManager().set_shutdown_at_application_end()

    assert signal_raising_listener.finished
    assert later_listener.notification_count == 1


def test_signal_while_the_shutdown_sets_the_event_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    exit_codes: list[int] = []
    monkeypatch.setattr(shutdown_manager.sys, "exit", exit_codes.append)
    monkeypatch.setattr(ShutdownManager(), "shutdown_event", SignalRaisingWhileSettingEvent())

    ShutdownManager().set_shutdown_at_application_end()

    assert exit_codes == []


def test_signal_after_the_grace_starts_a_new_grace() -> None:
    """
    The first listener ends the grace and raises a signal, which interrupts it.

    That signal starts a new grace, so the signal the second listener raises right after it is ignored.
    """
    interrupted_listener = GraceEndingSignalRaisingShutdownListener()
    later_listener = SignalRaisingShutdownListener()
    ShutdownManager().register_listener(interrupted_listener)
    ShutdownManager().register_listener(later_listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGINT)

    assert exit_info.value.code == ShutdownManager.INTERRUPT_EXIT_CODE
    assert not interrupted_listener.finished
    assert later_listener.finished


def test_second_init_keeps_the_installed_handlers() -> None:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

    ShutdownManager().init()

    assert signal.getsignal(signal.SIGTERM) == signal.SIG_IGN


@pytest.mark.usefixtures("no_signal_grace")
@pytest.mark.parametrize(("signal_number", "exit_code"), SIGNALS_AND_EXIT_CODES)
def test_signal_exits_after_the_grace(signal_number: signal.Signals, exit_code: int) -> None:
    ShutdownManager().set_shutdown_at_application_end()

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal_number)

    assert exit_info.value.code == exit_code


@pytest.mark.usefixtures("no_signal_grace")
def test_signal_after_the_grace_interrupts_a_listener_and_the_later_ones_still_run() -> None:
    signal_raising_listener = SignalRaisingShutdownListener()
    later_listener = CountingShutdownListener()
    ShutdownManager().register_listener(signal_raising_listener)
    ShutdownManager().register_listener(later_listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGINT)

    assert exit_info.value.code == ShutdownManager.INTERRUPT_EXIT_CODE
    assert not signal_raising_listener.finished
    assert later_listener.notification_count == 1
