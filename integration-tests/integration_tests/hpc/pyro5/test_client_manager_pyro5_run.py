from pathlib import Path

import dask.distributed as dd
import pytest
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_hpc.hpc_main_process import hpc_main_process

from integration_tests.hpc.hpc_data import server_config
from integration_tests.hpc.pyro5.hpc_pyro5_setup import Pyro5TestModule
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory


@pytest.mark.parametrize(
    "dask_cluster",
    [
        pytest.param(
            (2, 1),
            id="2 workers with 1 thread",
        ),
        pytest.param(
            (1, 2),
            marks=[pytest.mark.xfail(reason="the connection listener stops on a 'connecting' worker client"), pytest.mark.timeout(30)],
            id="1 worker with 2 threads",
        ),
        pytest.param(
            (4, 4),
            id="4 workers with 4 threads",
        ),
    ],
    indirect=True,
)
def test_a_pyro5_simulator_runs_every_step_on_a_dask_worker(dask_cluster: dd.Client, pyro_port: int, tmp_path: Path) -> None:
    repositories = RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK)
    pyro5module = Pyro5TestModule.generate_pyro5_module(tmp_path, pyro_port)

    hpc_main_process(
        dask_client=dask_cluster,
        server_config=server_config(),
        simulation_config=pyro5module.simulation_config,
        client_manager_config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=pyro5module.path),
        repositories=repositories,
    )

    stored = repositories.measurement_repository(client_id=pyro5module.client_id).all()
    assert [entry.values[0].value for entry in sorted(stored, key=lambda entry: entry.timestamp)] == [
        float(step) for step in range(1, pyro5module.steps + 1)
    ]
