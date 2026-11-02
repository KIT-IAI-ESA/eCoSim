import signal

import pytest

pytest_plugins = ["pytester"]


def test_failing_shutdown_in_teardown_still_gives_the_next_test_a_fresh_manager(pytester: pytest.Pytester) -> None:
    """
    In the teardown of the first inner test the event gets set and raises: the one expected error.

    The second inner test only passes if the fixture reset that shut down manager anyway.
    """
    pytester.makepyfile(
        """
        import threading

        from ecosim_common.tech.shutdown_manager import ShutdownManager


        class RaisingAfterSettingEvent(threading.Event):
            def set(self):
                super().set()
                raise RuntimeError("shutdown failed")


        def test_whose_teardown_fails_in_the_shutdown():
            ShutdownManager().shutdown_event = RaisingAfterSettingEvent()


        def test_after_the_failed_teardown_finds_no_shutdown():
            assert not ShutdownManager().is_shutdown()
        """,
    )

    result = pytester.runpytest_subprocess(timeout=60)

    result.assert_outcomes(passed=2, errors=1)


@pytest.mark.parametrize(
    ("signal_number", "exit_status"),
    [(signal.SIGINT, pytest.ExitCode.INTERRUPTED), (signal.SIGTERM, -signal.SIGTERM)],
)
def test_signal_stops_the_test_run(pytester: pytest.Pytester, signal_number: signal.Signals, exit_status: int) -> None:
    """The first inner test makes the signal hit the handlers left by 'reset_instance', not the ones Python starts with."""
    pytester.makepyfile(
        f"""
        import os


        def test_whose_teardown_resets_the_signal_handlers():
            pass


        def test_receiving_the_signal():
            os.kill(os.getpid(), {int(signal_number)})
        """,
    )

    result = pytester.runpytest_subprocess(timeout=60)

    assert result.ret == exit_status


def test_timeout_plugin_fails_a_hanging_test_and_the_run_continues(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import threading


        def test_hanging():
            threading.Event().wait()


        def test_next():
            pass
        """,
    )

    result = pytester.runpytest_subprocess("--timeout=1", timeout=60)

    result.assert_outcomes(passed=1, failed=1)
