import logging
import sys
from typing import Sequence

from ecosim_common.client.config.cli_arguments import CLIArguments
from ecosim_common.config import config_parser
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.one_line_errors import exits_with_one_line_errors
from ecosim_common.tech.shutdown_manager import ShutdownManager

from ecosim_client_pyro5.pyro_client import PyroClient


CONSOLE_SCRIPT = ConsoleScript(
    name="ecosim-client-pyro5",
    description="Connects a Python model served by a Pyro5 daemon to the eCoSim server. Start the server and the Pyro5 daemon first.",
    examples=("ecosim-client-pyro5 --config-file modules/grid/preferences.ini",),
)


@exits_with_one_line_errors(program_name=CONSOLE_SCRIPT.name)
def main(passed_arguments: Sequence[str] | None = None) -> None:
    args = CLIArguments(console_script=CONSOLE_SCRIPT, passed_arguments=passed_arguments)
    CONSOLE_SCRIPT.print_banner()

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
