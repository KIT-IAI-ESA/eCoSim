import signal

import pytest

pytest_plugins = ["pytester"]


def test_manager_shut_down_by_a_failing_teardown_does_not_reach_the_next_test(pytester: pytest.Pytester) -> None:
    pytester.makepyfile(
        """
        import threading

        from ecosim_common.tech.shutdown_manager import ShutdownManager


        class FailingEvent(threading.Event):
            def set(self):
                super().set()
                raise RuntimeError("shutdown failed")


        def test_first():
            ShutdownManager().shutdown_event = FailingEvent()


        def test_second():
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
    pytester.makepyfile(
        f"""
        import os


        def test_first():
            pass


        def test_second():
            os.kill(os.getpid(), {int(signal_number)})
        """,
    )

    result = pytester.runpytest_subprocess(timeout=60)

    assert result.ret == exit_status


def test_hanging_test_fails_and_the_run_continues(pytester: pytest.Pytester) -> None:
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
