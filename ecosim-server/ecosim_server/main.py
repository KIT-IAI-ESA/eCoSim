import logging
from time import sleep

from art import tprint
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_server.config.cli_arguments import CLIArguments
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories import Repositories, create_repositories
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurementType
from ecosim_server.server import Server


def main() -> None:
    tprint("eCoSimPy", font="tarty1", chr_ignore=True)
    print(f"Server - {get_module_version(name='ecosim-server')}")
    sleep(0.5)

    args = CLIArguments()

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

    repositories: Repositories = create_repositories(
        server_config=server_config,
        simulation_config=simulation_config,
    )

    server = Server(
        _server_config=server_config,
        _simulation_config=simulation_config,
        _repositories=repositories,
    )
    server.start()
    server.server_measurements.set_end(ServerTimeMeasurementType.SERVER_UPTIME)
    server.print_measurement_statistics()
    repositories.server_time_measurement_repository.put(server.server_measurements)

    ShutdownManager().set_shutdown_at_application_end()


if __name__ == "__main__":
    main()
