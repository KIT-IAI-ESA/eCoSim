from __future__ import annotations

import pytest
from ecosim_common.tech.one_line_errors import one_line_message
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.results import read_database_results
from tests.data.generate_server_config import generate_server_config


def test_a_refused_connection_ends_in_one_line_that_names_the_address() -> None:
    port = get_free_port()

    with pytest.raises(ConnectionError) as raised:
        read_database_results(database=generate_server_config(database_host="127.0.0.1", database_port=port).database)

    message = one_line_message(error=raised.value)
    assert "\n" not in message
    assert message.startswith(f"Cannot read the results from PostgreSQL at 127.0.0.1:{port}: ")


def test_a_refused_postgres_without_a_server_name_is_named_as_the_one_of_this_computer() -> None:
    port = get_free_port()

    with pytest.raises(ConnectionError, match=f"^Cannot read the results from PostgreSQL at port {port} of this computer: "):
        read_database_results(database=generate_server_config(database_host="", database_port=port).database)
