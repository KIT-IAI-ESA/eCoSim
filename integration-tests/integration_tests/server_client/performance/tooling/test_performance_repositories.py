from datetime import datetime
from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol

from integration_tests.server_client.performance.tooling.performance_repositories import PerformanceRepositories
from integration_tests.server_client.performance.tooling.performance_setup import current_machine
from integration_tests.tech.files.create_files import create_files


def test_the_latest_current_repository_of_protocol_and_machine_is_returned(tmp_path: Path) -> None:
    """
    This test creates different files in the test data directory and a newer file in the 'history' folder.
    Only the latest file of the test data directory must be used for current data.
    """
    machine_name = "local_my_laptop"
    create_files(
        tmp_path,
        f"2026-07-27_120000_dask_{machine_name}.jsonl",
        f"2026-07-28_120000_dask_{machine_name}.jsonl",
        f"2026-07-29_120000_tcp_socket_{machine_name}.jsonl",
        "2026-07-29_120000_dask_local_other.jsonl",
        f"2026-07-29_120000_dask_{machine_name}.txt",
    )
    create_files(tmp_path / "history", f"2026-07-30_120000_dask_{machine_name}.jsonl")

    repository = PerformanceRepositories.create(data_folder=tmp_path).get_expected_for(
        communication_protocol=CommunicationProtocol.DASK,
        machine_name=machine_name,
    )

    assert repository is not None
    assert repository.file_path().name == f"2026-07-28_120000_dask_{machine_name}.jsonl"


def test_without_a_matching_file_there_is_no_current_repository(tmp_path: Path) -> None:
    machine_name = "local_my_laptop"
    create_files(tmp_path, f"2026-07-28_120000_tcp_socket_{machine_name}.jsonl")
    assert (
        PerformanceRepositories.create(tmp_path).get_expected_for(
            communication_protocol=CommunicationProtocol.DASK,
            machine_name=machine_name,
        )
        is None
    )


def test_the_current_run_uses_the_same_repository_for_everything(tmp_path: Path) -> None:
    repositories = PerformanceRepositories.create(tmp_path)

    repository = repositories.get_repository_for_current_run(
        communication_protocol=CommunicationProtocol.DASK,
        machine_name=current_machine(),
    )

    assert (
        repositories.get_repository_for_current_run(
            communication_protocol=CommunicationProtocol.DASK,
            machine_name=current_machine(),
        )
        is repository
    )
    assert (repository.communication_protocol, repository.machine_name) == (CommunicationProtocol.DASK, current_machine())


def test_actual_and_expected_paths(tmp_path: Path) -> None:
    repositories = PerformanceRepositories.create(tmp_path)
    assert repositories._expected_folder == tmp_path  # noqa: SLF001
    assert repositories._actual_folder == tmp_path / "actual"  # noqa: SLF001


def test_the_summary_file_of_the_current_run_is_next_to_its_results(tmp_path: Path) -> None:
    repositories = PerformanceRepositories.create(tmp_path)

    result_path = repositories.get_repository_for_current_run(CommunicationProtocol.DASK, "local_my_laptop").file_path()
    summary_path = repositories.summary_file_path("local_my_laptop")

    assert summary_path.parent == result_path.parent


def test_the_summary_file_ends_with_the_correct_suffix(tmp_path: Path) -> None:
    repositories = PerformanceRepositories.create(tmp_path)

    summary_path = repositories.summary_file_path("local_my_laptop")

    assert summary_path.name.endswith("_results.log")


def test_the_actual_repositories_since_a_date(tmp_path: Path) -> None:
    create_files(
        tmp_path / PerformanceRepositories.ACTUAL_FOLDER_NAME,
        "2026-07-28_115959_dask_local_my_laptop.jsonl",
        "2026-07-28_120100_tcp_socket_local_my_laptop.jsonl",
        "2026-07-28_120000_dask_local_my_laptop.jsonl",
    )

    repositories = PerformanceRepositories.create(tmp_path).actual_repositories(since=datetime(2026, 7, 28, 12, 0, 0))

    assert [repository.file_path().name for repository in repositories] == [
        "2026-07-28_120000_dask_local_my_laptop.jsonl",
        "2026-07-28_120100_tcp_socket_local_my_laptop.jsonl",
    ]
