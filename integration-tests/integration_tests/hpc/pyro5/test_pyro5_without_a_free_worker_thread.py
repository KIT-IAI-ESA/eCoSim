from pathlib import Path

import dask.distributed as dd
import pytest
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_test_common.dask.wait_until_server_connection_listener_started import wait_until_server_connection_listener_started
from ecosim_test_common.tech.threading import exceptions_raised_in_threads

from integration_tests.hpc.pyro5.hpc_pyro5_setup import PYRO_NODE_IP, WORKER_NODE_IPS, Pyro5TestModule


@pytest.mark.parametrize("pyro_port", [PYRO_NODE_IP], indirect=True, ids=["pyro object on its own node"])
@pytest.mark.parametrize("dask_cluster_on_nodes", [{WORKER_NODE_IPS[0]: 1}], indirect=True, ids=["one worker with one thread"])
def test_a_pyro5_client_is_not_deployed_while_the_connection_listener_holds_the_only_worker_thread(
    dask_cluster_on_nodes: dd.Client,
    pyro_port: int,
    tmp_path: Path,
) -> None:
    module = Pyro5TestModule.generate_pyro5_module(tmp_path, pyro_port, pyro_host=PYRO_NODE_IP)

    with exceptions_raised_in_threads():
        server_thread = module.start_server()
        wait_until_server_connection_listener_started(dask_cluster_on_nodes)
        client_manager = ClientManager(ClientManagerConfig(host="localhost", port=9090, simulator_dir=module.path))
        client_manager.clients_start(module.simulation_config)

        is_deployed = client_manager.client_dict[module.client_id].is_boot_strapping_done.wait(timeout=10)

        ShutdownManager().set_shutdown_at_application_end()
        server_thread.join(timeout=30)

    assert not is_deployed
    assert not server_thread.is_alive()
