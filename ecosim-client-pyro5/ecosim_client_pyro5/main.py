import logging
import sys
from time import sleep

from ecosim_common.client.config.cli_arguments import CLIArguments
from ecosim_common.config import config_parser
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_common.tech.banner import print_banner

from ecosim_client_pyro5.pyro_client import PyroClient


def main() -> None:
    print_banner()
    print(f"Pyro5 Client - {get_module_version('ecosim_client_pyro5')}")
    sleep(0.5)
    args = CLIArguments()

    ShutdownManager().init()
    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)

    config = config_parser.ConfigParser(args.config_file())
    client = PyroClient.of(
        config_parser=config,
        config_override=args.config_overrides(),
    )
    client.start()
    client.wait_until_finished()

    ShutdownManager().set_shutdown_at_application_end()
    sys.exit(client.exit_code())


if __name__ == "__main__":
    main()
