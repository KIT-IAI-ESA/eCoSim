import dask.distributed as distributed
from ecosim_hpc.hpc_main_process import hpc_main_process
from integration_tests.hpc.hpc_data import client_manager_config, simulation_config, server_config
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory


def test_hpc_main_process(dask_client: distributed.Client) -> None:

    hpc_main_process(
        dask_client=dask_client,
        server_config=server_config(),
        simulation_config=simulation_config(),
        client_manager_config=client_manager_config(),
        repositories=RepositoriesInMemory(),
    )
