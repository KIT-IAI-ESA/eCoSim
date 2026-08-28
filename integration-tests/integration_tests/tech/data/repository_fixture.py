from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Generator, assert_never, cast

import pytest
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.server_config import DatabaseConfig
from testcontainers.postgres import PostgresContainer

POSTGRES_IMAGE = "postgres:16-alpine"


@pytest.fixture(scope="session")
def repository_postgres_container() -> Generator[PostgresContainer, Any, None]:
    # the ryuk reaper of testcontainers cannot be reached through a rootless container runtime
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    container = PostgresContainer(POSTGRES_IMAGE)
    container.start()
    yield container
    container.stop()


@pytest.fixture(
    scope="function",
    params=[
        DatabaseType.FILE,
        pytest.param(
            DatabaseType.POSTGRES,
            marks=pytest.mark.skipif(
                os.environ.get("CI") == "true",  # gitlab sets 'CI' and 'GITLAB_CI' true by default
                reason="Skipped in CI pipeline because it starts a postgres container",
            ),
        ),
    ],
    ids=lambda database_type: cast(DatabaseType, database_type).value,
)
def database_config(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> Generator[DatabaseConfig, Any, None]:
    """Runs a test once per database type, so once per 'Repositories' implementation.

    'generate_simple_test_server' builds the repositories of the database type it is handed,
    exactly like 'main.py' does. The postgres container only starts for 'DatabaseType.POSTGRES'.
    """
    database_type: DatabaseType = cast(DatabaseType, request.param)
    match database_type:
        case DatabaseType.FILE:
            yield _file_database_config(tmp_path)
        case DatabaseType.POSTGRES:
            yield _postgres_database_config(request.getfixturevalue("repository_postgres_container"))
        case _:
            assert_never(database_type)


def _file_database_config(directory: Path) -> DatabaseConfig:
    """The file repositories only read the directory, so the connection values stay empty."""
    return DatabaseConfig(
        host="",
        port=0,
        name="",
        schema="",
        username="",
        password="",
        ssl=False,
        drop_existing_schema=False,
        type=DatabaseType.FILE,
        directory=directory,
    )


def _postgres_database_config(container: PostgresContainer) -> DatabaseConfig:
    return DatabaseConfig(
        host=container.get_container_host_ip(),
        port=int(container.get_exposed_port(5432)),
        name=container.dbname,
        username=container.username,
        password=container.password,
        ssl=False,
        schema="postgres",  # the DTO metadata is bound to this schema whenever it is imported under pytest
        drop_existing_schema=True,
        type=DatabaseType.POSTGRES,
    )
