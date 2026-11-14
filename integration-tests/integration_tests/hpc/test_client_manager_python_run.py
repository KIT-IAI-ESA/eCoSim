import shutil
from datetime import datetime
from pathlib import Path

import dask.distributed as dd
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_hpc.hpc_main_process import hpc_main_process
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_test_common.resources.resource_utils import python_counter_config_path

from integration_tests.hpc.hpc_data import server_config
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory
from integration_tests.test_data.test_client_data import TestClientData


def test_a_python_model_next_to_its_ini_runs_every_step_on_a_dask_worker(dask_client: dd.Client, tmp_path: Path) -> None:
    # the directory holds counter.py, which would start the Pyro5 client without the [python] section
    shutil.copytree(src=python_counter_config_path().parent, dst=tmp_path / "counter")
    client_data = TestClientData.with_output(simulator_name="counter", model_name="counter", output_name="count")
    simulation_config = SimulationConfig(
        clients=[client_data.to_client_simulator_config()],
        start_date=datetime(2025, 1, 1),
        logical_delays=[],
        pace=1.0,
        steps=5,
        step_size_in_ms=1_000,
        restore=False,
    )
    repositories = RepositoriesInMemory.for_communication_protocol(CommunicationProtocol.DASK)

    hpc_main_process(
        dask_client=dask_client,
        server_config=server_config(),
        simulation_config=simulation_config,
        client_manager_config=ClientManagerConfig(host="localhost", port=9090, simulator_dir=tmp_path),
        repositories=repositories,
    )

    stored = repositories.measurement_repository(client_id=client_data.to_client_simulator_config().client_id).all()
    assert [entry.values[0].value for entry in sorted(stored, key=lambda entry: entry.timestamp)] == [1.0, 2.0, 3.0, 4.0, 5.0]
