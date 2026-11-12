from pathlib import Path

import dask.distributed as dd
import pytest
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources import resource_utils
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData
from ecosim_test_common.test_data.mock_dask_client import MockDaskClient


def test_clients_start_fails_naming_every_configured_simulator_missing_from_the_simulators_directory(dask_client: dd.Client, tmp_path: Path) -> None:
    simulation_config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=resource_utils.resource_path_file("hpc/modules/simulation.json"),
        steps=10,
    )
    client_manager = ClientManager(config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path))

    with pytest.raises(RuntimeError) as error:
        client_manager.clients_start(simulation_config=simulation_config)

    assert all(str(client.client_id) in str(error.value) for client in simulation_config.clients)


def test_pyro5_clients_run_on_the_scheduler_node_but_not_on_its_first_worker(
    dask_client: dd.Client,
    mock_dask_client: MockDaskClient,
    tmp_path: Path,
) -> None:
    """
    Every house module becomes a pyro5 simulator (its ini file and an empty .py file). The mocked dask cluster has a
    scheduler on 10.0.0.1 and three workers: the first one (assumed to run the listener), one on another node and
    one more on the scheduler node. Each pyro5 client must be submitted only to a worker on the scheduler node that
    does not run the server's dask connection listener: the same node, so the client reaches its Pyro simulator via
    localhost, but not the first worker, which is assumed to run that listener (the scheduler itself is no worker).
    """
    HouseSimulationData.copy_config_files_to(tmp_path)
    for module in HouseSimulationData.MODULES:
        (tmp_path / module / "simulator.py").touch()
    mock_dask_client.set_scheduler_address("tcp://10.0.0.1:8786")
    mock_dask_client.set_worker_addresses(("tcp://10.0.0.1:1", "tcp://10.0.0.2:2", "tcp://10.0.0.1:3"))

    client_manager = ClientManager(config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path))
    client_manager.clients_start(
        simulation_config=SimulationConfig.of_config_file_and_params(simulation_config_file=HouseSimulationData.SIMULATION_CONFIG_FILE, steps=10),
        dask_client_overwrite=mock_dask_client,
    )

    assert [call.kwargs["workers"] for call in mock_dask_client.sync.call_args_list] == [["tcp://10.0.0.1:3"]] * len(HouseSimulationData.MODULES)
