import logging
import sys
from typing import Sequence

from ecosim_common.client.config.cli_arguments import CLIArguments
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.tech.logger.logger import ESPLogger, init_logger
from ecosim_common.tech.one_line_errors import exits_with_one_line_errors
from ecosim_common.tech.shutdown_manager import ShutdownManager

from ecosim_client_matlab.matlab_client import MatlabClient


CONSOLE_SCRIPT = ConsoleScript(
    name="ecosim-client-matlab",
    description="Runs a model written as MATLAB scripts for the eCoSim server. Needs MATLAB and Python 3.12. Start the server first.",
    examples=("ecosim-client-matlab --config-file Modules/battery/preferences.ini",),
)


@exits_with_one_line_errors(program_name=CONSOLE_SCRIPT.name)
def main(passed_arguments: Sequence[str] | None = None) -> None:
    args = CLIArguments(console_script=CONSOLE_SCRIPT, passed_arguments=passed_arguments)
    CONSOLE_SCRIPT.print_banner()

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
