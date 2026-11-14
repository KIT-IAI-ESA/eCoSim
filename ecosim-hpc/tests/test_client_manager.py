import shutil
from pathlib import Path

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


def test_a_directory_with_model_files_of_two_kinds_stops_the_start_before_any_client_starts(dask_client: dd.Client, tmp_path: Path) -> None:
    shutil.copytree(src=resource_utils.resource_path_file("hpc/modules"), dst=tmp_path, dirs_exist_ok=True)
    (tmp_path / "house" / "helper.py").touch()
    simulation_config = SimulationConfig.of_config_file_and_params(simulation_config_file=tmp_path / "simulation.json", steps=10)
    client_manager = ClientManager(config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path))

    with pytest.raises(ValueError, match="helper.py, house.fmu"):
        client_manager.clients_start(simulation_config=simulation_config)

    assert len(client_manager.client_dict) == 0
