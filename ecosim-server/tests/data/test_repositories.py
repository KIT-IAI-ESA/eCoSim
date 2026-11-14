from __future__ import annotations

from pathlib import Path

import pytest
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.tech.one_line_errors import one_line_message
from ecosim_common.tech.port_utils import get_free_port
from ecosim_server.data.repositories import Repositories, create_repositories
from ecosim_server.data.repositories_file_based import RepositoriesFileBased
from tests.data.generate_server_config import generate_server_config
from tests.data.generate_simulation_config import generate_simulation_config_from_file


def test_the_file_database_type_creates_the_file_based_repositories(tmp_path: Path) -> None:
    repositories: Repositories = create_repositories(
        server_config=generate_server_config(database_type=DatabaseType.FILE, database_directory=tmp_path),
        simulation_config=generate_simulation_config_from_file(),
    )

    assert isinstance(repositories, RepositoriesFileBased)


def test_an_unsupported_database_type_fails(tmp_path: Path) -> None:
    unsupported_config = generate_server_config(
        database_type="mysql",  # type: ignore[arg-type] # deliberately not a DatabaseType to hit the fallback
        database_directory=tmp_path,
    )

    with pytest.raises(Exception, match="Unsupported database type"):
        create_repositories(
            server_config=unsupported_config,
            simulation_config=generate_simulation_config_from_file(),
        )


def test_a_postgres_that_refuses_the_connection_ends_in_one_line_with_the_way_to_files(tmp_path: Path) -> None:
    port = get_free_port()
    server_config = generate_server_config(database_host="127.0.0.1", database_port=port, database_directory=tmp_path)

    with pytest.raises(ConnectionError) as error_info:
        create_repositories(server_config=server_config, simulation_config=generate_simulation_config_from_file())

    message = one_line_message(error=error_info.value)
    assert "\n" not in message
    assert message.startswith(f"Cannot use PostgreSQL at 127.0.0.1:{port}: ")
    assert message.endswith(". To write the results as files instead, pass --database-type file")


def test_a_refused_postgres_without_a_server_name_is_named_as_the_one_of_this_computer(tmp_path: Path) -> None:
    port = get_free_port()
    server_config = generate_server_config(database_host="", database_port=port, database_directory=tmp_path)

    with pytest.raises(ConnectionError, match=f"^Cannot use PostgreSQL at port {port} of this computer: "):
        create_repositories(server_config=server_config, simulation_config=generate_simulation_config_from_file())
