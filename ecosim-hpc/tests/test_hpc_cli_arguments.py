from pathlib import Path

import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_test_common.esp_monkey_patch import ESPMonkeyPatch
from ecosim_test_common.exit_code_and_error_line import exit_code_and_error_line


def test_communication_protocol() -> None:
    cli_arguments = HPCServerCliArguments()
    assert cli_arguments.communication_protocol() == CommunicationProtocol.DASK


def test_unset_dask_options_take_their_defaults() -> None:
    cli_arguments = HPCServerCliArguments()

    assert cli_arguments.network_interface() is None
    assert cli_arguments.threads_per_worker() == HPCServerCliArguments.DEFAULT_THREADS_PER_WORKER
    assert cli_arguments.scheduler_file() == Path.cwd() / HPCServerCliArguments.DEFAULT_SCHEDULER_FILE


def test_given_network_interface_is_kept_and_the_thread_count_becomes_an_int(
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.set_sys_arg("--network-interface", "enp3s0")
    esp_monkey_patch.set_sys_arg("--threads-per-worker", "4")

    cli_arguments = HPCServerCliArguments()

    assert cli_arguments.network_interface() == "enp3s0"
    assert cli_arguments.threads_per_worker() == 4


def test_absolute_scheduler_file_overrides_the_call_path(
    esp_monkey_patch: ESPMonkeyPatch,
) -> None:
    esp_monkey_patch.set_sys_arg("--scheduler-file", "/shared/scheduler.json")

    assert HPCServerCliArguments().scheduler_file() == Path("/shared/scheduler.json")


@pytest.mark.parametrize("threads_per_worker", ["0", "-1"])
def test_threads_per_worker_must_be_positive(
    esp_monkey_patch: ESPMonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    threads_per_worker: str,
) -> None:
    esp_monkey_patch.set_sys_arg("--threads-per-worker", threads_per_worker)

    exit_code, error_line = exit_code_and_error_line(command=HPCServerCliArguments, capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line.endswith(f"error: argument --threads-per-worker: must be a whole number of at least 1, not '{threads_per_worker}'")
