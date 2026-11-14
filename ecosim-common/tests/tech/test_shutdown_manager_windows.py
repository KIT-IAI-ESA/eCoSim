import signal
import sys

import pytest

from ecosim_common.tech.shutdown_manager import ShutdownManager
from tests.tech.shutdown_listeners import CountingShutdownListener


def test_a_break_signal_shuts_down_like_terminate() -> None:
    # a skip and not a skipif mark, because mypy knows SIGBREAK only behind a check of the platform
    if sys.platform != "win32":
        pytest.skip("SIGBREAK exists on Windows only")
    ShutdownManager().init()
    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGBREAK)

    assert exit_info.value.code == ShutdownManager.TERMINATE_EXIT_CODE
    assert listener.notification_count == 1


def test_the_windows_break_handler_shuts_down_like_terminate_until_the_reset(monkeypatch: pytest.MonkeyPatch) -> None:
    # SIGUSR1 stands in for SIGBREAK, so the Windows branch also runs where SIGBREAK does not exist
    if sys.platform == "win32":
        pytest.skip("SIGUSR1 does not exist on Windows")
    monkeypatch.setattr(target=sys, name="platform", value="win32")
    monkeypatch.setattr(target=signal, name="SIGBREAK", value=signal.SIGUSR1, raising=False)
    ShutdownManager().init()
    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGUSR1)
    ShutdownManager.reset_instance()

    assert exit_info.value.code == ShutdownManager.TERMINATE_EXIT_CODE
    assert listener.notification_count == 1
    assert signal.getsignal(signal.SIGUSR1) == signal.SIG_DFL
