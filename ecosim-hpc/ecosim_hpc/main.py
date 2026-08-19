import logging

from art import tprint
from dask import distributed
from ecosim_common.tech.dask.init_dask import init_dask
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc import client_manager_config
from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_hpc.hpc_main_process import hpc_main_process
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories_db import RepositoriesDB


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
    cli_arguments = HPCServerCliArguments()
    if cli_arguments.interactive():
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
    log_level = logging.DEBUG if cli_arguments.debug_enabled() else logging.INFO
    init_logger(log_level=log_level)
    init_dask(
        log_level=log_level,
        client=dask_client,
    )
    server_config = ServerConfig.of_cli_args(cli_arguments)
    simulation_config = SimulationConfig.of_config_file_and_params(
        simulation_config_file=cli_arguments.simulation_config(),
        steps=cli_arguments.simulation_steps(),
        step_size_override=cli_arguments.step_size_override(),
        pace=cli_arguments.pace(),
        restore=cli_arguments.restore_simulation_run(),
    )

    hpc_main_process(
        dask_client=dask_client,
        server_config=server_config,
        simulation_config=simulation_config,
        client_manager_config=client_manager_config.ClientManagerConfig.of_server_config_and_cli_args(
            server_config=server_config,
            cli_args=cli_arguments,
        ),
        repositories=RepositoriesDB.create(
            server_config=server_config,
            simulation_config=simulation_config,
        ),
    )


if __name__ == "__main__":
    main()
