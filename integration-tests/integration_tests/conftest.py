import pytest
from ecosim_test_common import *  # noqa: F401,F403 # import all fixtures
from integration_tests.test_data.server_client.pre_set_two_clients_fixture import *  # noqa: F401,F403
from integration_tests.tech.data.repository_fixture import *  # noqa: F401,F403 # import the 'Repositories' fixtures


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Marks every test that is not a performance test as an integration test."""
    for item in items:
        if item.get_closest_marker("performance") is None:
            item.add_marker(pytest.mark.integration)
