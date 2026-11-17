import logging
import sys
from typing import Sequence

from ecosim_common.config import config_parser
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_common_fmpy.config.fmpy_cli_arguments import FMPyCliArguments
from ecosim_common_fmpy.config.validate_fmu_file_or_error import validate_fmu_file_or_error

from ecosim_client_fmu_v2.fmu2_client import FMU2Client


CONSOLE_SCRIPT = ConsoleScript(
    name="ecosim-client-fmu-v2",
    description="Runs an FMI 2.0 FMU for the eCoSim server. Start the server first.",
    examples=(
        "ecosim-client-fmu-v2 --config-file Modules/house/preferences.ini",
        "ecosim-client-fmu-v2 --config-file Modules/house/preferences.ini --server-host 192.168.1.20 --server-port 1234",
        "ecosim-client-fmu-v2 --config-file Modules/house/preferences.ini --validate-fmu-file-only",
    ),
)


def main(passed_arguments: Sequence[str] | None = None) -> None:
    args = FMPyCliArguments(console_script=CONSOLE_SCRIPT, passed_arguments=passed_arguments)
    CONSOLE_SCRIPT.print_banner()
    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)
    ShutdownManager().init()

    config = config_parser.ConfigParser(args.config_file())

    if args.validate_fmu_file_only():
        validate_fmu_file_or_error(config=config, fmi_major_version=2)
        return

    client = FMU2Client.create(
        config_parser=config,
        config_override=args.config_overrides(),
    )

    client.start()
    client.wait_until_finished()

    ShutdownManager().set_shutdown_at_application_end()
    sys.exit(client.exit_code())


if __name__ == "__main__":
    main()
