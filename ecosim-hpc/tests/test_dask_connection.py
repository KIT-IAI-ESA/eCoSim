from pathlib import Path
from typing import Generator
from unittest import mock

import pytest
from dask import distributed
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_hpc.dask_connection import connect_or_start_dask_cluster
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch


@pytest.fixture
def initialize() -> Generator[mock.MagicMock, None, None]:
    with mock.patch("ecosim_hpc.dask_connection.initialize") as initialize_mock:
        yield initialize_mock


@pytest.fixture
def client_class() -> Generator[mock.MagicMock, None, None]:
    with mock.patch("ecosim_hpc.dask_connection.Client") as client_class_mock:
        yield client_class_mock


def test_batch_mode_returns_a_client_created_after_dask_mpi_started_the_cluster_with_its_defaults(
    initialize: mock.MagicMock,
    client_class: mock.MagicMock,
) -> None:
    """'Client()' finds the scheduler through the address that 'initialize' sets in the Dask config."""
    calls = mock.Mock()
    calls.attach_mock(initialize, "initialize")
    calls.attach_mock(client_class, "client_class")

    dask_client = connect_or_start_dask_cluster(HPCServerCliArguments())

    assert calls.mock_calls == [mock.call.initialize(), mock.call.client_class()]
    assert dask_client is client_class.return_value


def test_batch_mode_passes_the_network_interface(initialize: mock.MagicMock, client_class: mock.MagicMock, esp_monkey_patch: ESPMonkeyPatch) -> None:
    esp_monkey_patch.set_sys_arg("--network-interface", "enp3s0")

    with mock.patch("ecosim_hpc.dask_connection.get_ip_interface"):
        connect_or_start_dask_cluster(HPCServerCliArguments())

    initialize.assert_called_once_with(interface="enp3s0")


def test_batch_mode_rejects_an_unknown_network_interface_before_mpi_starts(
    initialize: mock.MagicMock,
    client_class: mock.MagicMock,
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.set_sys_arg("--network-interface", "does_not_exist")

    with pytest.raises(ValueError, match="does_not_exist"):
        connect_or_start_dask_cluster(HPCServerCliArguments())

    initialize.assert_not_called()


def test_batch_mode_passes_the_thread_count(initialize: mock.MagicMock, client_class: mock.MagicMock, esp_monkey_patch: ESPMonkeyPatch) -> None:
    esp_monkey_patch.set_sys_arg("--threads-per-worker", "4")

    connect_or_start_dask_cluster(HPCServerCliArguments())

    initialize.assert_called_once_with(nthreads=4)


def test_interactive_mode_connects_through_the_given_scheduler_file(esp_monkey_patch: ESPMonkeyPatch, tmp_path: Path) -> None:
    scheduler_file = tmp_path / "custom_scheduler.json"
    esp_monkey_patch.set_sys_arg("--interactive")
    esp_monkey_patch.set_sys_arg("--scheduler-file", str(scheduler_file))

    with distributed.LocalCluster(n_workers=0, dashboard_address=None, scheduler_kwargs={"scheduler_file": str(scheduler_file)}) as cluster:
        with connect_or_start_dask_cluster(HPCServerCliArguments()) as dask_client:
            assert dask_client.scheduler_info()["address"] == cluster.scheduler_address


def test_interactive_mode_rejects_a_missing_scheduler_file(client_class: mock.MagicMock, esp_monkey_patch: ESPMonkeyPatch, tmp_path: Path) -> None:
    scheduler_file = tmp_path / "missing.json"
    esp_monkey_patch.set_sys_arg("--interactive")
    esp_monkey_patch.set_sys_arg("--scheduler-file", str(scheduler_file))

    with pytest.raises(SystemExit, match=str(scheduler_file)):
        connect_or_start_dask_cluster(HPCServerCliArguments())

    client_class.assert_not_called()
