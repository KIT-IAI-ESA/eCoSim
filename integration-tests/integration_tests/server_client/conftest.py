from typing import Any, Generator

import pytest

from ecosim_common.tech.shutdown_manager import ShutdownManager


@pytest.fixture(scope="session", autouse=True)
def teardown_shutdown_manager() -> Generator[None, Any, None]:
    """runs once after all tests"""
    yield
    ShutdownManager().set_shutdown_at_application_end()
