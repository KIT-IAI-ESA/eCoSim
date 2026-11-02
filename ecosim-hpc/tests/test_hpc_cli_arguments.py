from pathlib import Path

import pytest
from _pytest.capture import CaptureFixture
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch


def test_communication_protocol(
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_hpc_cli_sys_args()

    cli_arguments = HPCServerCliArguments()
    assert cli_arguments.communication_protocol() == CommunicationProtocol.DASK


def test_cli_arguments_within_sql_alchemy(
    remove_pytest_variables: None,
    capsys: CaptureFixture[str],
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_hpc_cli_sys_args()

    from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base

    assert SimControlDB_Base is not None

    logs = capsys.readouterr()
    assert logs.err == ""
    assert logs.out == ""


def test_dask_options_default_to_no_choice_and_the_common_scheduler_file(
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_hpc_cli_sys_args()

    cli_arguments = HPCServerCliArguments()

    assert cli_arguments.network_interface() is None
    assert cli_arguments.threads_per_worker() is None
    assert cli_arguments.scheduler_file() == Path.cwd() / "scheduler.json"


def test_dask_options_are_read(
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_hpc_cli_sys_args()
    esp_monkey_patch.set_sys_arg("--network-interface", "enp3s0")
    esp_monkey_patch.set_sys_arg("--threads-per-worker", "4")
    esp_monkey_patch.set_sys_arg("--scheduler-file", "/shared/scheduler.json")

    cli_arguments = HPCServerCliArguments()

    assert cli_arguments.network_interface() == "enp3s0"
    assert cli_arguments.threads_per_worker() == 4
    assert cli_arguments.scheduler_file() == Path("/shared/scheduler.json")


@pytest.mark.parametrize("threads_per_worker", ["0", "-1"])
def test_threads_per_worker_must_be_positive(
    esp_monkey_patch: ESPMonkeyPatch,
    threads_per_worker: str,
) -> None:
    esp_monkey_patch.remove_pytest_sys_args()
    esp_monkey_patch.set_hpc_cli_sys_args()
    esp_monkey_patch.set_sys_arg("--threads-per-worker", threads_per_worker)

    with pytest.raises(ValueError, match="--threads-per-worker"):
        HPCServerCliArguments()
