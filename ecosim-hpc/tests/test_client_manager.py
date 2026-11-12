from pathlib import Path

import dask.distributed as dd
import pytest
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources import resource_utils
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData
from ecosim_test_common.test_data.mock_dask_client import MockDaskClient

from tests.client_manager_setup import start_house_simulators_as_pyro5_clients


def test_clients_start_fails_naming_every_configured_simulator_missing_from_the_simulators_directory(dask_client: dd.Client, tmp_path: Path) -> None:
    simulation_config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=resource_utils.resource_path_file("hpc/modules/simulation.json"),
        steps=10,
    )
    client_manager = ClientManager(config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path))

    with pytest.raises(RuntimeError) as error:
        client_manager.clients_start(simulation_config=simulation_config)

    assert all(str(client.client_id) in str(error.value) for client in simulation_config.clients)


WORKER_1 = "tcp://10.0.0.1:1"
WORKER_ON_SCHEDULER_NODE = "tcp://10.0.0.1:2"
WORKER_ON_OTHER_NODE = "tcp://10.0.0.2:1"
WORKER_2_ON_OTHER_NODE = "tcp://10.0.0.2:2"


@pytest.mark.parametrize(
    ("threads_by_worker", "allowed_workers"),
    [
        pytest.param(
            {WORKER_1: 1, WORKER_ON_OTHER_NODE: 1, WORKER_ON_SCHEDULER_NODE: 1},
            [WORKER_ON_SCHEDULER_NODE],
            id="first worker with 1 thread",
        ),
        pytest.param(
            {WORKER_1: 1, WORKER_ON_OTHER_NODE: 4, WORKER_ON_SCHEDULER_NODE: 2},
            [WORKER_ON_SCHEDULER_NODE],
            id="other node with more threads",
        ),
        pytest.param(
            {WORKER_1: 2, WORKER_ON_OTHER_NODE: 1},
            [WORKER_1],
            id="first worker with a thread to spare",
        ),
        pytest.param(
            {WORKER_1: 2, WORKER_ON_OTHER_NODE: 1, WORKER_ON_SCHEDULER_NODE: 1},
            [WORKER_1, WORKER_ON_SCHEDULER_NODE],
            id="both workers on the scheduler node",
        ),
    ],
)
def test_pyro5_clients_run_on_the_scheduler_node_beside_the_connection_listener(
    dask_client: dd.Client,
    mock_dask_client: MockDaskClient,
    tmp_path: Path,
    threads_by_worker: dict[str, int],
    allowed_workers: list[str],
) -> None:
    """
    The pyro5 clients reach their Pyro simulator via localhost, so they must run on a worker on the scheduler node
    (the scheduler itself is no worker). The first worker is assumed to run the server's dask connection listener,
    which holds one of its threads for the whole run: it can take pyro5 clients only with a thread to spare.
    """
    start_house_simulators_as_pyro5_clients(tmp_path=tmp_path, mock_dask_client=mock_dask_client, threads_by_worker=threads_by_worker)

    assert [call.kwargs["workers"] for call in mock_dask_client.sync.call_args_list] == [allowed_workers] * len(HouseSimulationData.MODULES)


@pytest.mark.parametrize(
    "threads_by_worker",
    [
        pytest.param({WORKER_1: 1, WORKER_ON_OTHER_NODE: 2}, id="only the first worker on the scheduler node, with 1 thread"),
        pytest.param({WORKER_ON_OTHER_NODE: 2, WORKER_2_ON_OTHER_NODE: 2}, id="no worker on the scheduler node"),
        pytest.param({WORKER_1: 1}, id="a single worker with 1 thread"),
    ],
)
def test_clients_start_fails_without_a_worker_for_the_pyro5_clients_on_the_scheduler_node(
    dask_client: dd.Client,
    mock_dask_client: MockDaskClient,
    tmp_path: Path,
    threads_by_worker: dict[str, int],
) -> None:
    """Without an allowed worker, the pyro5 clients would be submitted without any restriction and could run on a node
    whose localhost does not reach their Pyro simulator."""
    with pytest.raises(RuntimeError):
        start_house_simulators_as_pyro5_clients(tmp_path=tmp_path, mock_dask_client=mock_dask_client, threads_by_worker=threads_by_worker)
