from pathlib import Path

from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources.simulations.house_simulation_data import HouseSimulationData
from ecosim_test_common.test_data.mock_dask_client import MockDaskClient


def start_house_simulators_as_pyro5_clients(
    tmp_path: Path,
    mock_dask_client: MockDaskClient,
    threads_by_worker: dict[str, int],
    scheduler_address: str = "tcp://10.0.0.1:8786",
) -> None:
    """Every house module becomes a pyro5 simulator: its ini file and an empty .py file."""
    HouseSimulationData.copy_config_files_to(tmp_path)
    for module in HouseSimulationData.MODULES:
        (tmp_path / module / "simulator.py").touch()
    mock_dask_client.set_scheduler_address(scheduler_address)
    mock_dask_client.set_workers(threads_by_worker)
    ClientManager(config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path)).clients_start(
        simulation_config=SimulationConfig.of_config_file_and_params(simulation_config_file=HouseSimulationData.SIMULATION_CONFIG_FILE, steps=10),
        dask_client_overwrite=mock_dask_client,
    )
