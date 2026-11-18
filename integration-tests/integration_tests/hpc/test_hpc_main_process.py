import signal
import subprocess
import sys
import time
from pathlib import Path

import dask.distributed as distributed
import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_hpc.hpc_main_process import hpc_main_process
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS
from integration_tests.hpc.hpc_client_modules import ClientKind, write_client_module, write_fmu2_module_that_names_a_missing_fmu
from integration_tests.hpc.hpc_data import client_manager_config, fmu_files, server_config, simulation_config, single_client_simulation_config
from integration_tests.hpc.hpc_run_in_a_subprocess import start_hpc_run_in_a_subprocess
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


def test_a_client_start_that_fails_stops_the_server_and_fails_the_main_process(dask_client: distributed.Client, tmp_path: Path) -> None:
    # kept in this process, the Dask client is closed after the run
    repositories = RepositoriesInMemory()

    # tmp_path has no simulator folders
    with pytest.raises(RuntimeError, match="house#house"):
        hpc_main_process(
            dask_client=dask_client,
            server_config=server_config(),
            simulation_config=simulation_config(),
            client_manager_config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path),
            repositories=repositories,
        )

    assert repositories.simulation_state_repository.current() is SimulationState.FAILED


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no SIGINT for another process")
def test_ctrl_c_while_the_server_waits_for_a_client_ends_the_run_as_stopped(tmp_path: Path) -> None:
    output_file = tmp_path / "output.log"
    client_id = write_fmu2_module_that_names_a_missing_fmu(simulator_dir=tmp_path)
    run = start_hpc_run_in_a_subprocess(simulator_dir=tmp_path, client_id=client_id, output_file=output_file)
    try:
        wait_until_the_server_waits_for_its_client(run=run, output_file=output_file)

        run.send_signal(signal.SIGINT)

        assert run.wait(timeout=WAIT_TIMEOUT_IN_SECONDS) == ShutdownManager.INTERRUPT_EXIT_CODE
    finally:
        run.kill()
    assert "Reason: stopped by Ctrl-C or a kill signal" in output_file.read_text(encoding="utf-8")


def wait_until_the_server_waits_for_its_client(run: subprocess.Popen[bytes], output_file: Path) -> None:
    deadline = time.monotonic() + WAIT_TIMEOUT_IN_SECONDS
    while "Server: Waiting for 1 client to connect" not in output_file.read_text(encoding="utf-8"):
        if run.poll() is not None or time.monotonic() > deadline:
            raise TimeoutError(f"the server did not wait for its client:\n{output_file.read_text(encoding='utf-8')}")
        time.sleep(0.1)
