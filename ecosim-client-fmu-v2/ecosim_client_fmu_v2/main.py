import logging
from time import sleep
from art import tprint

from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_common.client.config.cli_arguments import CLIArguments

from ecosim_common.config import config_parser
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import ESPLogger, init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager


def main() -> None:
    tprint("eCoSimPy", font="tarty1", chr_ignore=True)
    print(f"FMUv2 Client - {get_module_version('ecosim_client_fmu_v2')}")
    sleep(0.5)

    args = CLIArguments()

    ShutdownManager().init()
    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)

    main_logger = ESPLogger("main")

    config = config_parser.ConfigParser(args.config_file())
    client = FMU2Client(config, args.config_overrides())
    main_logger.debug("Calling client.connect()")
    client.start()
    client.wait_until_finished()
    main_logger.debug("Reached end")

    ShutdownManager().set_shutdown_at_application_end()


if __name__ == '__main__':
    main()
