from typing import Generator, Any

import psycopg2
import pytest
from psycopg2._psycopg import connection
from psycopg2.extras import DictCursor
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
def db_connection(postgres_container: PostgresContainer) -> Generator[connection, Any, None]:
    conn = psycopg2.connect(
        host=postgres_container.get_container_host_ip(),
        port=postgres_container.get_exposed_port(5432),
        database=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password,
        cursor_factory=DictCursor,
    )

    yield conn
    conn.close()
