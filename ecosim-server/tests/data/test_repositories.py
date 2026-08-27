from __future__ import annotations

from pathlib import Path

import pytest
from ecosim_common.config.database_type import DatabaseType
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
