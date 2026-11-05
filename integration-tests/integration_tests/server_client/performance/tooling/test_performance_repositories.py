from pathlib import Path

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from integration_tests.server_client.performance.tooling.performance_setup import current_machine

from integration_tests.server_client.performance.tooling.performance_repositories import PerformanceRepositories
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


def test_the_current_run_writes_to_one_repository_per_protocol_on_this_machine(tmp_path: Path) -> None:
    repositories = PerformanceRepositories.create(tmp_path)

    repository = repositories.get_repository_for_current_run(CommunicationProtocol.DASK)

    assert repositories.get_repository_for_current_run(CommunicationProtocol.DASK) is repository
    assert (repository.communication_protocol, repository.machine_name) == (CommunicationProtocol.DASK, current_machine())
