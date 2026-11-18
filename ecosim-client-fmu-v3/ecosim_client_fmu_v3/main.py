import logging
import sys
from typing import Sequence

from ecosim_common.config import config_parser
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.one_line_errors import exits_with_one_line_errors
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_common_fmpy.config.fmpy_cli_arguments import FMPyCliArguments
from ecosim_common_fmpy.config.validate_fmu_file_or_error import validate_fmu_file_or_error

from ecosim_client_fmu_v3.fmu3_client import FMU3Client


CONSOLE_SCRIPT = ConsoleScript(
    name="ecosim-client-fmu-v3",
    description="Runs an FMI 3.0 FMU for the eCoSim server. Start the server first.",
    examples=(
        "ecosim-client-fmu-v3 --config-file modules/controller/preferences.ini",
        "ecosim-client-fmu-v3 --config-file modules/controller/preferences.ini --validate-fmu-file-only",
    ),
)


@exits_with_one_line_errors(program_name=CONSOLE_SCRIPT.name)
def main(passed_arguments: Sequence[str] | None = None) -> None:
    args = FMPyCliArguments(console_script=CONSOLE_SCRIPT, passed_arguments=passed_arguments)
    CONSOLE_SCRIPT.print_banner()

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
