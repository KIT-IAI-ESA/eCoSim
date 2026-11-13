from pathlib import Path

import dask.distributed as dd
import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_hpc.hpc_main_process import hpc_main_process
from ecosim_test_common.tech.threading import exceptions_raised_in_threads

from integration_tests.hpc.hpc_data import server_config
from integration_tests.hpc.pyro5.hpc_pyro5_setup import Pyro5TestModule
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory

PYRO_NODE_IP = "127.0.0.111"
# the Pyro object listens on its own node only, as a daemon with an explicit host does
pytestmark = pytest.mark.parametrize("pyro_port", [PYRO_NODE_IP], indirect=True, ids=["pyro object on its own node"])


def test_a_pyro5_client_on_any_node_runs_every_step_with_the_pyro_object_on_its_own_node(
    dask_cluster_on_nodes: dd.Client,
    pyro_port: int,
    tmp_path: Path,
) -> None:
    module = Pyro5TestModule.generate_pyro5_module(tmp_path, pyro_port, pyro_host=PYRO_NODE_IP)
    repositories = RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK)

    with exceptions_raised_in_threads() as thread_exceptions:
        _run(dask_cluster_on_nodes, module, repositories)

    assert not thread_exceptions
    stored = sorted(repositories.measurement_repository(client_id=module.client_id).all(), key=lambda entry: entry.timestamp)
    assert [entry.values[0].value for entry in stored] == [float(step) for step in range(1, module.steps + 1)]


@pytest.mark.parametrize(
    "pyro_host",
    [
        pytest.param("localhost", id="localhost of the worker's node"),
        pytest.param("127.0.0.5", id="a node without the Pyro object"),
    ],
)
def test_the_run_fails_when_the_pyro5_client_cannot_reach_its_pyro_object(
    dask_cluster_on_nodes: dd.Client,
    pyro_port: int,
    tmp_path: Path,
    pyro_host: str,
) -> None:
    module = Pyro5TestModule.generate_pyro5_module(tmp_path, pyro_port, pyro_host=pyro_host)
    repositories = RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK)

    with pytest.raises(RuntimeError, match="Lost client"):
        _run(dask_cluster_on_nodes, module, repositories)

    assert repositories.measurement_repository(client_id=module.client_id).all() == []


def _run(dask_client: dd.Client, module: Pyro5TestModule, repositories: RepositoriesInMemory) -> None:
    hpc_main_process(
        dask_client=dask_client,
        server_config=server_config(),
        simulation_config=module.simulation_config,
        client_manager_config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=module.path),
        repositories=repositories,
    )
