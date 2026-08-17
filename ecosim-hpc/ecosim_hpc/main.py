import logging
import threading
from time import sleep

from art import tprint
from dask import distributed
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.dask.init_dask import init_dask
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_common.tech.system_arguments import overwrite_system_argument
from ecosim_hpc.client_manager import ClientManager
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurementType
from ecosim_server.server import Server


def get_mpi_interface() -> str:
    from subprocess import check_output

    # Determine infiniband interface
    ifconfig = check_output(["ifconfig", "-s"]).decode().split("\n")
    for line in ifconfig:
        if line[:2] == "ib":
            return line.split(" ")[0]
        if line[:3] == "eth":
            return line.split(" ")[0]
    raise ValueError("Defined connection required")


def main() -> None:
    # TODO: find a better solution
    # TODO_OSR: check the todo above
    overwrite_system_argument("--communication-protocol", CommunicationProtocol.DASK.name)

    args = HPCServerCliArguments()
    if args.interactive():
        dask_client = distributed.Client(scheduler_file="scheduler.json")
        tprint("eCoSimHPC", font="tarty1", chr_ignore=True)
        print(f"Server - {get_module_version(name='ecosim-server')}")

    else:
        from dask_mpi import initialize

        interface = get_mpi_interface()
        initialize(interface=interface, nthreads=2)
        dask_client = distributed.Client()
        tprint("eCoSimHPC", font="tarty1", chr_ignore=True)
        print(f"Server - {get_module_version(name='ecosim-server')}")

    ShutdownManager().init()
    log_level = logging.DEBUG if args.debug_enabled() else logging.INFO
    init_logger(log_level=log_level)
    init_dask(
        log_level=log_level,
        client=dask_client,
    )

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

    server = Server(
        _server_config=server_config,
        _simulation_config=simulation_config,
        _repositories=repositories,
    )

    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    client_manager = ClientManager(args)
    client_manager.clients_start(simulation_config)
    server_thread.join()
    server.server_measurements.set_end(ServerTimeMeasurementType.SERVER_UPTIME)
    server.print_measurement_statistics()
    repositories.server_time_measurement_repository.put(server.server_measurements)

    dask_client.run(ShutdownManager().set_shutdown_at_application_end)
    ShutdownManager().set_shutdown_at_application_end()
    sleep(5)
    # dask_client.shutdown()
    dask_client.close()


if __name__ == "__main__":
    main()
