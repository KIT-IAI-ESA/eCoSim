import logging
import subprocess
import sys
from pathlib import Path

import dask.distributed as distributed
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.dask.init_dask import init_dask
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_hpc.hpc_main_process import hpc_main_process

from integration_tests.hpc.hpc_data import server_config, single_client_simulation_config
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory


def start_hpc_run_in_a_subprocess(simulator_dir: Path, client_id: ClientID, output_file: Path) -> subprocess.Popen[bytes]:
    """Runs hpc_main_process with the signal handlers in its own process for a test with a real signal."""
    module = "integration_tests.hpc.hpc_run_in_a_subprocess"
    command = [sys.executable, "-m", module, str(simulator_dir), client_id.model_name, client_id.simulator_name]
    with output_file.open("wb") as output:
        return subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)


def _run_with_signal_handlers(simulator_dir: Path, client_id: ClientID) -> None:
    dask_client = distributed.Client(n_workers=2, threads_per_worker=2)
    ShutdownManager().init()
    init_logger(log_level=logging.INFO)
    init_dask(log_level=logging.INFO, client=dask_client)
    hpc_main_process(
        dask_client=dask_client,
        server_config=server_config(),
        simulation_config=single_client_simulation_config(client_id=client_id),
        client_manager_config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=simulator_dir),
        repositories=RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK),
    )


if __name__ == "__main__":
    _run_with_signal_handlers(simulator_dir=Path(sys.argv[1]), client_id=ClientID(model_name=sys.argv[2], simulator_name=sys.argv[3]))
