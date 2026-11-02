import shutil
from pathlib import Path
from typing import Generator

import pytest
from tests.tech.db.postgres_test_cluster import PostgresTestCluster
from tests.tech.db.postgres_test_process import find_postgres_binaries


@pytest.fixture(scope="session")
def postgres_binaries() -> Path:
    binaries = find_postgres_binaries()
    if binaries is None:
        pytest.skip("PostgreSQL is not installed: initdb was not found")
    return binaries


@pytest.fixture(scope="session")
def plain_cluster(
    postgres_binaries: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[PostgresTestCluster, None, None]:
    cluster = PostgresTestCluster.start(
        binaries=postgres_binaries,
        directory=tmp_path_factory.mktemp("plain_cluster"),
        tls=False,
    )
    yield cluster
    cluster.stop()


@pytest.fixture(scope="session")
def tls_cluster(
    postgres_binaries: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Generator[PostgresTestCluster, None, None]:
    if shutil.which("openssl") is None:
        pytest.skip("openssl is not installed, so there is no certificate for the server")
    cluster = PostgresTestCluster.start(
        binaries=postgres_binaries,
        directory=tmp_path_factory.mktemp("tls_cluster"),
        tls=True,
    )
    yield cluster
    cluster.stop()
