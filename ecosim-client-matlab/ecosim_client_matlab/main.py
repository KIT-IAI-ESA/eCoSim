import logging
import sys
from time import sleep

from art import tprint
from ecosim_common.client.config.cli_arguments import CLIArguments
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import ESPLogger, init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager

from ecosim_client_matlab.matlab_client import MatlabClient


def main() -> None:
    tprint("eCoSimPy", font="tarty1", chr_ignore=True)
    print(f"Matlab Client - {get_module_version('ecosim_client_matlab')}")
    sleep(0.5)

    args = CLIArguments()

    ShutdownManager().init()
    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)

    main_logger = ESPLogger("main")

    config_parser = ConfigParser(args.config_file())
    client = MatlabClient.of(
        config_parser=config_parser,
        config_overrides=args.config_overrides(),
    )
    main_logger.debug("Calling client.connect()")
    client.start()
    client.wait_until_finished()
    main_logger.debug("Reached end")

    ShutdownManager().set_shutdown_at_application_end()
    sys.exit(client.exit_code())


if __name__ == "__main__":
    main()
