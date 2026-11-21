import os
import time
from pathlib import Path
from typing import Any, Generator

import pytest
from tests.tech.db import postgres_test_process
from tests.tech.db.postgres_test_cluster import PostgresTestCluster
from tests.tech.db.postgres_test_process import run_command, stop_postgres


def _is_running(process_id: int) -> bool:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            os.kill(process_id, 0)
        except ProcessLookupError:
            return False
        time.sleep(0.05)
    return True


class _Interruption:
    def __init__(
        self,
        directory: Path,
        exception_type: type[BaseException],
    ) -> None:
        self.directory = directory
        self.exception_type = exception_type
        self.server_process_id: int | None = None

    def raise_exception(self) -> None:
        self.server_process_id = int((self.directory / "data" / "postmaster.pid").read_text(encoding="utf-8").splitlines()[0])
        raise self.exception_type("interrupted during the start")


@pytest.fixture
def directory(
    tmp_path: Path,
    postgres_binaries: Path,
) -> Generator[Path, None, None]:
    yield tmp_path
    stop_postgres(binaries=postgres_binaries, directory=tmp_path, check=False)


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, RuntimeError])
def test_a_failure_of_the_first_statement_stops_the_server(
    monkeypatch: pytest.MonkeyPatch,
    postgres_binaries: Path,
    directory: Path,
    exception_type: type[BaseException],
) -> None:
    interruption = _Interruption(directory=directory, exception_type=exception_type)
    monkeypatch.setattr(PostgresTestCluster, "execute", lambda *arguments, **keyword_arguments: interruption.raise_exception())

    with pytest.raises(exception_type, match="interrupted during the start"):
        PostgresTestCluster.start(binaries=postgres_binaries, directory=directory, tls=False)

    assert interruption.server_process_id is not None
    assert not _is_running(interruption.server_process_id)


def test_an_interruption_right_after_the_server_came_up_stops_the_server(
    monkeypatch: pytest.MonkeyPatch,
    postgres_binaries: Path,
    directory: Path,
) -> None:
    interruption = _Interruption(directory=directory, exception_type=KeyboardInterrupt)

    def run_and_interrupt_after_the_start(*command: Any, **keyword_arguments: Any) -> None:
        run_command(*command, **keyword_arguments)
        if "start" in command:
            interruption.raise_exception()

    monkeypatch.setattr(postgres_test_process, "run_command", run_and_interrupt_after_the_start)

    with pytest.raises(KeyboardInterrupt):
        PostgresTestCluster.start(binaries=postgres_binaries, directory=directory, tls=False)

    assert interruption.server_process_id is not None
    assert not _is_running(interruption.server_process_id)


def test_a_failure_before_the_server_came_up_raises_the_original_error(
    postgres_binaries: Path,
    tmp_path: Path,
) -> None:
    with pytest.raises(FileNotFoundError):
        PostgresTestCluster.start(binaries=postgres_binaries, directory=tmp_path / "missing", tls=False)
