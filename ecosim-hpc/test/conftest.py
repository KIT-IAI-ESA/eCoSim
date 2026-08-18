import sys
from typing import Any, Generator

import _pytest.runner as pytest_runner
import pytest


@pytest.fixture
def remove_pytest_variables(monkeypatch: pytest.MonkeyPatch) -> Generator[None, Any, None]:
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(pytest_runner, "_update_current_test_var", lambda *a, **k: None)

    buffer_pytest = None
    buffer_pytest_index = -1
    pytest_sys_arg_in_use = any("pytest" in arg for arg in sys.argv)
    if pytest_sys_arg_in_use:
        pytest_index = next(i for i, arg in enumerate(sys.argv) if "pytest" in arg)
        buffer_pytest = sys.argv.pop(pytest_index)
        buffer_pytest_index = pytest_index

    yield

    if buffer_pytest is not None:
        sys.argv.insert(buffer_pytest_index, buffer_pytest)
