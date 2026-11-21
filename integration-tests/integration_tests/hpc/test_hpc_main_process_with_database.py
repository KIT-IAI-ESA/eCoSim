import os
from dataclasses import replace
from typing import Any, Generator

import dask.distributed as distributed
import pytest
from ecosim_hpc.hpc_main_process import hpc_main_process
from ecosim_server.config.server_config import DatabaseConfig, ServerConfig
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.tech.threading import exceptions_raised_in_threads
from integration_tests.hpc.hpc_data import client_manager_config, fmu_files, server_config, simulation_config
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="module")
def postgres_container() -> Generator[PostgresContainer, Any, None]:
    # the ryuk reaper of testcontainers cannot be reached through a rootless container runtime
    os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")
    container = PostgresContainer("postgres:16-alpine")
    container.start()
    yield container
    container.stop()


@skip_unless_fmpy_loads(*fmu_files())
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

    with exceptions_raised_in_threads() as thread_exceptions:
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
            # a thread that died is reported even when the run itself fails
            assert not thread_exceptions, f"A thread died: {thread_exceptions}"


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
            schema="postgres",
            drop_existing_schema=True,
        ),
    )
