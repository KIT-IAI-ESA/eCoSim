import shutil
from pathlib import Path
from typing import Generator

import pytest
from tests.tech.db.password_sources import PasswordSources
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


@pytest.fixture
def password_sources(
    plain_cluster: PostgresTestCluster,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> PasswordSources:
    # the settings of whoever runs the tests must not decide them
    monkeypatch.delenv(name="PGPASSWORD", raising=False)
    monkeypatch.setenv(name="PGPASSFILE", value=str(tmp_path / "no_such_file"))
    monkeypatch.setenv(name="HOME", value=str(tmp_path))
    return PasswordSources(cluster=plain_cluster, directory=tmp_path, monkeypatch=monkeypatch)


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
