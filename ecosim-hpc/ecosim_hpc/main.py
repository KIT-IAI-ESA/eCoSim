import logging
from typing import Sequence

from ecosim_common.tech.dask.init_dask import init_dask
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_hpc import client_manager_config
from ecosim_hpc.config.cli_arguments import CONSOLE_SCRIPT, HPCServerCliArguments
from ecosim_hpc.dask_connection import connect_or_start_dask_cluster
from ecosim_hpc.hpc_main_process import hpc_main_process
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import create_repositories


def main(passed_arguments: Sequence[str] | None = None) -> None:
    cli_arguments = HPCServerCliArguments(passed_arguments=passed_arguments)
    dask_client = connect_or_start_dask_cluster(cli_arguments)
    CONSOLE_SCRIPT.print_banner()

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
        repositories=create_repositories(
            server_config=server_config,
            simulation_config=simulation_config,
        ),
    )


if __name__ == "__main__":
    main()
