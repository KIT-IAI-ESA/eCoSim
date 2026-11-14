import logging
import os
import signal
import threading
from pathlib import Path

import dask.distributed as distributed
import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_hpc.hpc_main_process import SERVER_THREAD_NAME, hpc_main_process
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS
from ecosim_test_common.wait_until_logged import wait_until_logged
from integration_tests.hpc.hpc_client_modules import ClientKind, write_client_module, write_fmu2_module_that_names_a_missing_fmu
from integration_tests.hpc.hpc_data import client_manager_config, fmu_files, server_config, simulation_config, single_client_simulation_config
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory

# a thread that dies in the main process would otherwise only be a warning
pytestmark = pytest.mark.filterwarnings("error::pytest.PytestUnhandledThreadExceptionWarning")


@skip_unless_fmpy_loads(*fmu_files())
def test_hpc_main_process(dask_client: distributed.Client) -> None:
    hpc_main_process(
        dask_client=dask_client,
        server_config=server_config(),
        simulation_config=simulation_config(),
        client_manager_config=client_manager_config(),
        repositories=RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK),
    )


def test_failed_server_run_closes_the_dask_client_and_fails_the_main_process(dask_client: distributed.Client, tmp_path: Path) -> None:
    # without a Pyro5 daemon the client fails when the simulation starts
    client_id = write_client_module(simulator_dir=tmp_path, kind=ClientKind.PYRO5)

    with pytest.raises(RuntimeError, match=str(client_id)):
        hpc_main_process(
            dask_client=dask_client,
            server_config=server_config(),
            simulation_config=single_client_simulation_config(client_id=client_id),
            client_manager_config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path),
            repositories=RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK),
        )

    assert dask_client.status == "closed"


def test_a_client_start_that_fails_ends_the_server_before_the_error_leaves_the_main_process(dask_client: distributed.Client, tmp_path: Path) -> None:
    # a test before this one can leave a server thread behind
    threads_before = _server_threads()

    _start_without_the_simulator_folders(dask_client=dask_client, simulator_dir=tmp_path)

    assert _server_threads() <= threads_before


def test_a_client_start_that_fails_leaves_the_error_line_to_the_main_process(
    dask_client: distributed.Client,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _start_without_the_simulator_folders(dask_client=dask_client, simulator_dir=tmp_path)

    assert [record.getMessage() for record in caplog.records if record.levelno >= logging.ERROR] == []


def test_a_signal_while_the_server_waits_for_a_client_logs_no_error_in_the_server_thread(
    dask_client: distributed.Client,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    ShutdownManager().init()
    client_id = write_fmu2_module_that_names_a_missing_fmu(simulator_dir=tmp_path)
    threads_before = _server_threads()
    # the main process waits for the server thread, so another thread presses Ctrl-C
    threading.Thread(target=_interrupt_once_the_server_waits, kwargs={"caplog": caplog}, daemon=True).start()

    with pytest.raises(SystemExit):
        hpc_main_process(
            dask_client=dask_client,
            server_config=server_config(),
            simulation_config=single_client_simulation_config(client_id=client_id),
            client_manager_config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path),
            repositories=RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK),
        )
    # the server thread fails on the closed Dask client and can log after the main process ended
    for server_thread in _server_threads() - threads_before:
        server_thread.join(timeout=WAIT_TIMEOUT_IN_SECONDS)

    assert [record.getMessage() for record in caplog.records if record.levelno >= logging.ERROR and record.threadName == SERVER_THREAD_NAME] == []


def _interrupt_once_the_server_waits(caplog: pytest.LogCaptureFixture) -> None:
    wait_until_logged(caplog=caplog, message_start="Still waiting for", timeout_in_seconds=WAIT_TIMEOUT_IN_SECONDS)
    os.kill(os.getpid(), signal.SIGINT)


def _start_without_the_simulator_folders(dask_client: distributed.Client, simulator_dir: Path) -> None:
    # the client start fails while the server waits for the clients
    with pytest.raises(RuntimeError, match="house#house"):
        hpc_main_process(
            dask_client=dask_client,
            server_config=server_config(),
            simulation_config=simulation_config(),
            client_manager_config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=simulator_dir),
            repositories=RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK),
        )


def _server_threads() -> set[threading.Thread]:
    return {thread for thread in threading.enumerate() if thread.name == SERVER_THREAD_NAME}
