import logging
import sys
from time import sleep

from ecosim_common.config import config_parser
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_common_fmpy.config.fmpy_cli_arguments import FMPyCliArguments
from ecosim_common_fmpy.config.validate_fmu_file_or_error import validate_fmu_file_or_error
from ecosim_common.tech.banner import print_banner

from ecosim_client_fmu_v3.fmu3_client import FMU3Client


def main() -> None:
    print_banner()
    print(f"FMUv3 Client - {get_module_version('ecosim_client_fmu_v3')}")
    sleep(0.5)

    args = FMPyCliArguments()

    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)
    ShutdownManager().init()

    config = config_parser.ConfigParser(args.config_file())

    if args.get_additional_parameter("validate-fmu-file-only"):
        validate_fmu_file_or_error(config=config, fmi_major_version=3)
        return

    client = FMU3Client.of(
        config_parser=config,
        config_override=args.config_overrides(),
    )
    client.start()
    client.wait_until_finished()

    ShutdownManager().set_shutdown_at_application_end()
    sys.exit(client.exit_code())


if __name__ == "__main__":
    main()
