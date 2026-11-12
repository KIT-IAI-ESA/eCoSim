from typing import Dict
from unittest.mock import Mock

import pytest


class MockDaskClient(Mock):
    """A very primitive mock of a dask client. It is meant to grow over time with more sophisticated functionality."""

    def set_scheduler_address(self, address: str) -> None:
        self.scheduler_info.return_value = {"address": address}

    def set_workers(self, threads_by_address: Dict[str, int]) -> None:
        # like dask, ncores maps the address of every worker to its number of threads
        self.ncores.return_value = dict(threads_by_address)


@pytest.fixture
def mock_dask_client() -> MockDaskClient:
    return MockDaskClient()
