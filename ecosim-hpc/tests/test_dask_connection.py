import subprocess
import sys
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest
from dask import distributed
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_hpc.dask_connection import connect_dask_client
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch


@pytest.fixture
def initialize() -> Generator[mock.MagicMock, None, None]:
    with mock.patch("dask_mpi.initialize") as initialize_mock, mock.patch.object(distributed, "Client"):
        yield initialize_mock


@pytest.fixture
def command_line(esp_monkey_patch: ESPMonkeyPatch) -> ESPMonkeyPatch:
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_hpc_cli_sys_args()
    return esp_monkey_patch


def test_batch_mode_leaves_the_unset_options_to_dask_mpi(initialize: mock.MagicMock, command_line: ESPMonkeyPatch) -> None:
    connect_dask_client(HPCServerCliArguments())

    initialize.assert_called_once_with()


@pytest.mark.parametrize("network_interface", ["enp3s0", "eno1", "eth0", "ib0"])
def test_batch_mode_passes_the_network_interface(initialize: mock.MagicMock, command_line: ESPMonkeyPatch, network_interface: str) -> None:
    command_line.set_sys_arg("--network-interface", network_interface)

    with mock.patch("ecosim_hpc.dask_connection.get_ip_interface"):
        connect_dask_client(HPCServerCliArguments())

    initialize.assert_called_once_with(interface=network_interface)


def test_batch_mode_rejects_an_unknown_network_interface_before_mpi_starts(initialize: mock.MagicMock, command_line: ESPMonkeyPatch) -> None:
    command_line.set_sys_arg("--network-interface", "does_not_exist")

    with pytest.raises(ValueError, match="does_not_exist"):
        connect_dask_client(HPCServerCliArguments())

    initialize.assert_not_called()


def test_batch_mode_passes_the_thread_count(initialize: mock.MagicMock, command_line: ESPMonkeyPatch) -> None:
    command_line.set_sys_arg("--threads-per-worker", "4")

    connect_dask_client(HPCServerCliArguments())

    initialize.assert_called_once_with(nthreads=4)


def test_interactive_mode_connects_through_the_given_scheduler_file(command_line: ESPMonkeyPatch, tmp_path: Path) -> None:
    scheduler_file = tmp_path / "custom_scheduler.json"
    command_line.set_sys_arg("--interactive")
    command_line.set_sys_arg("--scheduler-file", str(scheduler_file))

    with distributed.LocalCluster(n_workers=0, dashboard_address=None, scheduler_kwargs={"scheduler_file": str(scheduler_file)}) as cluster:
        with connect_dask_client(HPCServerCliArguments()) as dask_client:
            assert dask_client.scheduler_info()["address"] == cluster.scheduler_address


def test_interactive_mode_rejects_a_missing_scheduler_file(command_line: ESPMonkeyPatch, tmp_path: Path) -> None:
    scheduler_file = tmp_path / "missing.json"
    command_line.set_sys_arg("--interactive")
    command_line.set_sys_arg("--scheduler-file", str(scheduler_file))

    with mock.patch.object(distributed, "Client") as client, pytest.raises(SystemExit, match=str(scheduler_file)):
        connect_dask_client(HPCServerCliArguments())

    client.assert_not_called()


def test_application_stops_right_away_without_the_default_scheduler_file(tmp_path: Path) -> None:
    options = ["--server-config", "unused", "--simulation-config", "unused", "--simulator-dir", "unused", "--steps", "1"]

    result = subprocess.run(
        [sys.executable, "-m", "ecosim_hpc.main", "--interactive", *options],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 1
    assert f"The scheduler file '{tmp_path / 'scheduler.json'}' does not exist" in result.stderr
