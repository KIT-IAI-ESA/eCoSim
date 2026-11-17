import signal
import sys

import pytest

from ecosim_common.tech.shutdown_manager import ShutdownManager
from tests.tech.shutdown_listeners import CountingShutdownListener


def test_a_break_signal_shuts_down_like_terminate() -> None:
    # mypy knows SIGBREAK only behind a check of the platform
    if sys.platform != "win32":
        pytest.skip("SIGBREAK exists on Windows only")
    ShutdownManager().init()
    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGBREAK)

    assert exit_info.value.code == ShutdownManager.TERMINATE_EXIT_CODE
    assert listener.notification_count == 1


def test_a_second_terminate_signal_shuts_down_like_terminate_until_the_reset() -> None:
    if sys.platform == "win32":
        pytest.skip("SIGUSR1 does not exist on Windows")
    ShutdownManager().init(terminate_signals=(signal.SIGTERM, signal.SIGUSR1))
    listener = CountingShutdownListener()
    ShutdownManager().register_listener(listener)

    with pytest.raises(SystemExit) as exit_info:
        signal.raise_signal(signal.SIGUSR1)
    ShutdownManager.reset_instance()

    assert exit_info.value.code == ShutdownManager.TERMINATE_EXIT_CODE
    assert listener.notification_count == 1
    assert signal.getsignal(signal.SIGUSR1) == signal.SIG_DFL
