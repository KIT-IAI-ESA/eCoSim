import os
import threading
from contextlib import contextmanager
from dataclasses import replace
from typing import Any, Generator, Iterator

import dask.distributed as distributed
import pytest
from ecosim_hpc.hpc_main_process import hpc_main_process
from ecosim_server.config.server_config import DatabaseConfig, ServerConfig
from ecosim_server.data.repositories_db import RepositoriesDB
from integration_tests.hpc.hpc_data import client_manager_config, server_config, simulation_config
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="module")
def postgres_container() -> Generator[PostgresContainer, Any, None]:
    # the ryuk reaper of testcontainers cannot be reached through a rootless container runtime
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    yield container
    container.stop()


@pytest.mark.skipif(
    os.environ.get("CI") == "true",  # gitlab sets 'CI' and 'GITLAB_CI' true by default
    reason="Skipped in CI pipeline because it starts a postgres container",
)
def test_hpc_main_process_with_database_repositories(
    dask_client: distributed.Client,
    postgres_container: PostgresContainer,
) -> None:
    """
    Runs 'hpc_main_process' the way 'main.py' runs it: on a 'RepositoriesDB' instead of an in memory one.

    The server hands its state to the dask worker that listens for connections, and that state reaches the
    repositories - so the SQLAlchemy engine behind them has to be pickled, which it cannot be.
    """
    config = _server_config_on(postgres_container)
    simulation = simulation_config()

    with _exceptions_raised_in_threads() as thread_exceptions:
        try:
            hpc_main_process(
                dask_client=dask_client,
                server_config=config,
                simulation_config=simulation,
                client_manager_config=client_manager_config(),
                repositories=RepositoriesDB.create(
                    server_config=config,
                    simulation_config=simulation,
                ),
            )
        finally:
            # the run collapses in its own way once the server is gone, so this is asserted either way
            assert not thread_exceptions, f"The server thread died: {thread_exceptions}"


def _server_config_on(postgres_container: PostgresContainer) -> ServerConfig:
    return replace(
        server_config(),
        database=DatabaseConfig(
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            name=postgres_container.dbname,
            username=postgres_container.username,
            password=postgres_container.password,
            ssl=False,
            schema="postgres",  # the DTO metadata is bound to this schema whenever it is imported under pytest
            drop_existing_schema=True,
        ),
    )


@contextmanager
def _exceptions_raised_in_threads() -> Iterator[list[BaseException | None]]:
    """The server runs in a thread of its own, where an exception only ever reaches 'threading.excepthook'."""
    raised: list[BaseException | None] = []
    previous_hook = threading.excepthook

    def record(args: threading.ExceptHookArgs) -> None:
        raised.append(args.exc_value)
        previous_hook(args)

    threading.excepthook = record
    try:
        yield raised
    finally:
        threading.excepthook = previous_hook
