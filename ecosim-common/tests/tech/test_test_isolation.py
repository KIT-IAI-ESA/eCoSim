import pytest

pytest_plugins = ["pytester"]


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
