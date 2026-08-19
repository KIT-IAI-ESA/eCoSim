import threading
from time import sleep

import dask.distributed as distributed
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurementType
from ecosim_server.server import Server


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

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    client_manager = ClientManager(client_manager_config)
    client_manager.clients_start(simulation_config)
    server_thread.join()
    server.server_measurements.set_end(ServerTimeMeasurementType.SERVER_UPTIME)
    server.print_measurement_statistics()
    repositories.server_time_measurement_repository.put(server.server_measurements)

    dask_client.run(ShutdownManager().set_shutdown_at_application_end)
    ShutdownManager().set_shutdown_at_application_end()

    sleep(5)
    dask_client.close()
