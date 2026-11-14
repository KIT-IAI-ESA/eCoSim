from time import sleep

import dask.distributed as distributed
from ecosim_common.tech.dask.shutdown_dask import shutdown_dask_workers
from ecosim_common.tech.parallel.error_recording_thread import ErrorRecordingThread
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.client_manager_config import ClientManagerConfig
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurementType
from ecosim_server.server import Server

SERVER_THREAD_NAME = "Server"


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

    server_thread = ErrorRecordingThread(target=server.start, name=SERVER_THREAD_NAME)
    server_thread.start()
    client_manager = ClientManager(client_manager_config)
    try:
        client_manager.clients_start(simulation_config)
        server_thread.join()
    except SystemExit:
        # the signal handler already closed the server and the Dask client, only the summary is missing
        server.print_run_summary()
        raise
    except Exception:
        # end the server while Dask still runs, so the error line comes last
        server.force_stop()
        server_thread.join()
        shutdown_dask_workers(dask_client)
        ShutdownManager().set_shutdown_at_application_end()
        raise
    try:
        if server_thread.error is not None:
            raise server_thread.error
        server.server_measurements.set_end(ServerTimeMeasurementType.SERVER_UPTIME)
        server.print_measurement_statistics()
        repositories.server_time_measurement_repository.put(server.server_measurements)
    finally:
        server.print_run_summary()
        shutdown_dask_workers(dask_client)
        ShutdownManager().set_shutdown_at_application_end()

        sleep(5)
        dask_client.close()
