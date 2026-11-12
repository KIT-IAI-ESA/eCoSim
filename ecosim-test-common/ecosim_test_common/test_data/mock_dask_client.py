from typing import Tuple
from unittest.mock import Mock

import pytest


class MockDaskClient(Mock):
    """A very primitive mock of a dask client. It is meant to grow over time with more sophisticated functionality."""

    def set_scheduler_address(self, address: str) -> None:
        self.scheduler_info.return_value = {"address": address}

    def set_worker_addresses(
        self,
        addresses: Tuple[str, ...],
        number_of_threads: int = 2,
    ) -> None:
        # ncores maps the address of every worker to its number of threads
        self.ncores.return_value = {address: number_of_threads for address in addresses}


@pytest.fixture
def mock_dask_client() -> MockDaskClient:
    return MockDaskClient()
