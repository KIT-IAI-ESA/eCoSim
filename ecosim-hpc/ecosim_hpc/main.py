import logging
from time import sleep
import dask.distributed as dd
import threading

from art import tprint
from ecosim_hpc.client_manager import ClientManager
from ecosim_server.config.cli_arguments import CLIArgumentsHPC
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.server import Dask_Server
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurementType
from ecosim_server.data.repositories import Repositories
from ecosim_hpc.data.repositories_db import RepositoriesDB


def main() -> None:
    tprint("eCoSimHPC", font="tarty1", chr_ignore=True)
    print(f"Server - {get_module_version(name='ecosim-server')}")
    sleep(0.5)

    dd.Client(processes=False)

    args = CLIArgumentsHPC()

    ShutdownManager().init()
    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)

    server_config = ServerConfig.of_cli_args(args)
    simulation_config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=args.simulation_config(),
        steps=args.simulation_steps(),
        step_size_override=args.step_size_override(),
        pace=args.pace(),
        restore=args.restore_simulation_run(),
    )

    repositories: Repositories = RepositoriesDB.create(
        server_config=server_config,
        simulation_config=simulation_config,
    )

    server = Dask_Server(server_config, simulation_config, repositories)

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    client_manager = ClientManager(args)
    client_manager.clients_start(simulation_config)
    server_thread.join()
    server.server_measurements.set_end(ServerTimeMeasurementType.SERVER_UPTIME)
    server.print_measurement_statistics()
    repositories.server_time_measurement_repository.put(server.server_measurements)

    # ShutdownManager().set_shutdown_at_application_end()  # If used, RuntimeError will occur due to loss of channel once simulation is complete


if __name__ == "__main__":
    main()
