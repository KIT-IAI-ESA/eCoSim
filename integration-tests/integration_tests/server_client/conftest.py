from .pre_sets.pre_set_two_clients import *  # type: ignore # noqa # import fixture
from typing import Any, Generator

import pytest
import dask.distributed as dd

from ecosim_common.tech.shutdown_manager import ShutdownManager


@pytest.fixture(scope="session", autouse=True)
def teardown_shutdown_manager() -> Generator[None, Any, None]:
    """runs once after all tests"""
    yield
    client = dd.get_client()
    for key in client.datasets.keys():
        print(key, client.get_dataset(key))
    ShutdownManager().set_shutdown_at_application_end()
    client.close()
