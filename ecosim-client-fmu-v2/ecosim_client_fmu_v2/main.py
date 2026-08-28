import logging
from time import sleep

from art import tprint
from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_common.config import config_parser
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_common_fmpy.config.fmpy_cli_arguments import FMPyCliArguments
from ecosim_common_fmpy.config.validate_fmu_file_or_error import validate_fmu_file_or_error
from ecosim_common_fmpy.tech.fix_lmxl_threading_issues import fix_lmxl_threading_issues


def main() -> None:
    fix_lmxl_threading_issues()

    tprint("eCoSimPy", font="tarty1", chr_ignore=True)
    print(f"FMUv2 Client - {get_module_version('ecosim_client_fmu_v2')}")
    sleep(0.5)

    args = FMPyCliArguments()
    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)
    ShutdownManager().init()

    config = config_parser.ConfigParser(args.config_file())

    if args.validate_fmu_file_only():
        validate_fmu_file_or_error(config)
        return

    client = FMU2Client(config, args.config_overrides())

    client.start()
    client.wait_until_finished()

    ShutdownManager().set_shutdown_at_application_end()


if __name__ == "__main__":
    main()
