from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import pytest
from ecosim_server.config.server_config import ServerConfig
from psycopg import sql
from tests.data.generate_server_config import generate_server_config
from tests.tech.db.postgres_test_process import (
    GROUP_REJECTED_ON_MAINTENANCE_DATABASE,
    HOST,
    SUPERUSER,
    SUPERUSER_PASSWORD,
    free_port,
    start_postgres,
    stop_postgres,
)

skip_in_ci = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Skipped in CI pipeline because it starts a postgres cluster",
)


@dataclass(frozen=True)
class PostgresTestCluster:
    binaries: Path
    directory: Path
    port: int
    tls: bool

    @staticmethod
    def start(
        binaries: Path,
        directory: Path,
        tls: bool,
    ) -> PostgresTestCluster:
        cluster = PostgresTestCluster(binaries=binaries, directory=directory, port=free_port(), tls=tls)
        try:
            start_postgres(binaries=binaries, directory=directory, port=cluster.port, tls=tls)
            cluster.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(GROUP_REJECTED_ON_MAINTENANCE_DATABASE)))
        except BaseException:
            stop_postgres(binaries=binaries, directory=directory, check=False)
            raise
        return cluster

    def stop(self) -> None:
        stop_postgres(binaries=self.binaries, directory=self.directory)

    def server_config(
        self,
        database_name: str,
        username: str = SUPERUSER,
        password: str = SUPERUSER_PASSWORD,
        ssl: bool | None = None,
        drop_existing_schema: bool = False,
        schema: str | None = None,
    ) -> ServerConfig:
        return generate_server_config(
            database_host=HOST,
            database_port=self.port,
            database_username=username,
            database_password=password,
            database_name=database_name,
            database_ssl=self.tls if ssl is None else ssl,
            database_drop_existing_schema=drop_existing_schema,
            database_schema=schema,
        )

    def _connect(self, database: str) -> psycopg.Connection[Any]:
        return psycopg.connect(
            host=HOST,
            port=self.port,
            user=SUPERUSER,
            password=SUPERUSER_PASSWORD,
            dbname=database,
            sslmode="require" if self.tls else "disable",
            autocommit=True,
        )

    def execute(
        self,
        statement: sql.SQL | sql.Composed,
        database: str = "postgres",
    ) -> None:
        with self._connect(database) as connection:
            connection.execute(statement)

    def fetch_value(
        self,
        query: str,
        parameter: str,
        database: str = "postgres",
    ) -> Any:
        with self._connect(database) as connection:
            row = connection.execute(query=sql.SQL(query), params=(parameter,)).fetchone()
        return row[0] if row else None

    def create_role(
        self,
        name: str,
        password: str,
        can_create_databases: bool = True,
    ) -> None:
        statement = sql.SQL("CREATE ROLE {} LOGIN PASSWORD {} {}").format(
            sql.Identifier(name),
            sql.Literal(password),
            sql.SQL("CREATEDB" if can_create_databases else "NOCREATEDB"),
        )
        self.execute(statement)

    def create_database(
        self,
        name: str,
        owner: str = SUPERUSER,
    ) -> None:
        self.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(name), sql.Identifier(owner)))

    def reject_on_maintenance_database(self, role: str) -> None:
        self.execute(sql.SQL("GRANT {} TO {}").format(sql.Identifier(GROUP_REJECTED_ON_MAINTENANCE_DATABASE), sql.Identifier(role)))

    def was_reached(
        self,
        database: str,
        username: str,
    ) -> bool:
        return f"database={database} user={username} " in (self.directory / "server.log").read_text(encoding="utf-8")

    def has_no_connections(self, username: str) -> bool:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.fetch_value(query="SELECT count(*) FROM pg_stat_activity WHERE usename = %s", parameter=username) == 0:
                return True
            time.sleep(0.05)
        return False

    def database_id(self, name: str) -> Any:
        return self.fetch_value(query="SELECT oid FROM pg_database WHERE datname = %s", parameter=name)

    def schema_exists(
        self,
        database: str,
        schema: str,
    ) -> bool:
        query = "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s"
        return self.fetch_value(query=query, parameter=schema, database=database) is not None

    def table_exists(
        self,
        database: str,
        schema: str,
        table: str,
    ) -> bool:
        return self.fetch_value(query="SELECT to_regclass(%s)", parameter=f"{schema}.{table}", database=database) is not None
