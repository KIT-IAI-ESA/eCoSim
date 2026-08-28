import _pytest.runner as pytest_runner
import pytest


@pytest.fixture
def remove_pytest_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Hides the running test from the code under test, so it takes its production branch.

    'ESPMonkeyPatch' already keeps 'pytest' out of 'sys.argv'; the environment variable is the
    remaining hint, and pytest sets it again before each test phase - hence the patched updater.
    """
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(pytest_runner, "_update_current_test_var", lambda *args, **kwargs: None)
