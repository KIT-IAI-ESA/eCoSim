import pytest

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_test_common.test_data.generate_connection_address import generate_unused_connection_address


@pytest.fixture
def address() -> ConnectionAddress:
    return generate_unused_connection_address()
