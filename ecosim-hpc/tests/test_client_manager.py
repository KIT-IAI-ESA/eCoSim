import shutil
from pathlib import Path
from unittest.mock import Mock

import dask.distributed as dd
import pytest
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources import resource_utils


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
    tmp_path: Path,
) -> None:
    modules = resource_utils.resource_path_file("hpc/modules/simulation.json").parent
    for module in ("house", "weather", "occupancy"):
        (tmp_path / module).mkdir()
        shutil.copy(modules / module / "preferences.ini", tmp_path / module)
        (tmp_path / module / "simulator.py").touch()
    client_manager = ClientManager(config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path))
    fake_dask_client = Mock()
    fake_dask_client.scheduler_info.return_value = {"address": "tcp://10.0.0.1:8786"}
    fake_dask_client.ncores.return_value = {"tcp://10.0.0.1:1": 1, "tcp://10.0.0.2:2": 1, "tcp://10.0.0.1:3": 1}

    client_manager.clients_start(
        simulation_config=SimulationConfig.of_config_file_and_params(simulation_config_file=modules / "simulation.json", steps=10),
        dask_client_overwrite=fake_dask_client,
    )

    assert [call.kwargs["workers"] for call in fake_dask_client.sync.call_args_list] == [["tcp://10.0.0.1:3"]] * 3
