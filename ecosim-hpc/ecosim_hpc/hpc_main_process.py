import threading
from time import sleep
from typing import override

import dask.distributed as distributed
from ecosim_common.tech.dask.shutdown_dask import shutdown_dask_workers
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurementType
from ecosim_server.server import Server


class _ServerThread(threading.Thread):
    """Keeps what the server raises, so the main process can end as failed."""

    error: BaseException | None = None

    @override
    def run(self) -> None:
        try:
            super().run()
        except BaseException as error:
            self.error = error


def hpc_main_process(
    dask_client: distributed.Client,
    server_config: ServerConfig,
    simulation_config: SimulationConfig,
    client_manager_config: ClientManagerConfig,
    repositories: Repositories,
) -> None:
    server = Server(
        _server_config=server_config,
        _simulation_config=simulation_config,
        _repositories=repositories,
    )

    server_thread = _ServerThread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    client_manager = ClientManager(client_manager_config)
    client_manager.clients_start(simulation_config)
    server_thread.join()
    try:
        if server_thread.error is not None:
            raise server_thread.error
        server.server_measurements.set_end(ServerTimeMeasurementType.SERVER_UPTIME)
        server.print_measurement_statistics()
        repositories.server_time_measurement_repository.put(server.server_measurements)
    finally:
        shutdown_dask_workers(dask_client)
        ShutdownManager().set_shutdown_at_application_end()

        sleep(5)
        dask_client.close()
