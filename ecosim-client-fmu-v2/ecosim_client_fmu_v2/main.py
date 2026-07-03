import logging
from time import sleep

import fmpy
from art import tprint
from ecosim_client_fmu_v2.fmu2_client import FMU2Client
from ecosim_client_fmu_v2.fmu2_config import FMU2Config
from ecosim_common.client.config.cli_arguments import CLIArguments
from ecosim_common.config import config_parser
from ecosim_common.config.app_config import AppConfigParameter
from ecosim_common.tech.deployment.module_version import get_module_version
from ecosim_common.tech.logger.logger import ESPLogger, init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager

# the following lines try to mitigate multi-threading issues resulting (indirectly) from the fmpy library
# s. `doc/dev/tech/multi_threading_fmpy.md` for details
try:
    import ctypes

    from lxml import etree

    lib = ctypes.CDLL(etree.__file__)
    lib.xmlSchemaInitTypes()

except Exception:
    pass


def main() -> None:
    tprint("eCoSimPy", font="tarty1", chr_ignore=True)
    print(f"FMUv2 Client - {get_module_version('ecosim_client_fmu_v2')}")
    sleep(0.5)

    args = CLIArguments(
        additional_parameters=[
            AppConfigParameter(
                name="validate-fmu-file-only",
                required=False,
                is_flag=True,
                help_text="Only validate the FMU file - no client will be started.",
            ),
        ],
    )

    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)
    main_logger = ESPLogger("main")
    ShutdownManager().init()
    config = config_parser.ConfigParser(args.config_file())

    if args.get_additional_parameter("validate-fmu-file-only"):
        fmu2_config = FMU2Config.of_config_parser(config)
        main_logger.debug("validate-fmu-file-only flag set -> only checking FMU file and then exiting")
        main_logger.info("Validating FMU file...")
        try:
            fmpy.read_model_description(fmu2_config.fmu_file, validate=True)
        except Exception as e:
            main_logger.error(f"Checking FMU file failed: {e}")
            raise e
        main_logger.info("Validating FMU file...completed. No errors found.")
        return

    client = FMU2Client(config, args.config_overrides())

    main_logger.debug("Calling client.connect()")
    client.start()
    client.wait_until_finished()
    main_logger.debug("Reached end")

    ShutdownManager().set_shutdown_at_application_end()


if __name__ == "__main__":
    main()
