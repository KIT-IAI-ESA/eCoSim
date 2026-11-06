from typing import Generator, Any

import psycopg
import pytest
from psycopg import Connection
from psycopg.rows import DictRow, dict_row
from testcontainers.postgres import PostgresContainer


@pytest.fixture(scope="function", autouse=True)
def postgres_container() -> Generator[PostgresContainer, Any, None]:
    container = (
        PostgresContainer("postgres:16-alpine", port=5432)
        # .with_bind_ports(5432, 5432) # deactivate comment to bind database to port 5432 -> necessary to look into database from ide
        .with_name("persistence_db")
    )

    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="function", autouse=True)
def db_connection(postgres_container: PostgresContainer) -> Generator[Connection[DictRow], Any, None]:
    conn = psycopg.connect(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        dbname=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password,
        row_factory=dict_row,
    )

    yield conn
    conn.close()
