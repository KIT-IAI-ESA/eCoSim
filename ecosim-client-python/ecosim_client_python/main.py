import logging
import sys
from typing import Sequence

from ecosim_common.client.config.cli_arguments import CLIArguments
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.tech.logger.logger import init_logger
from ecosim_common.tech.one_line_errors import exits_with_one_line_errors
from ecosim_common.tech.shutdown_manager import ShutdownManager

from ecosim_client_python.python_client import PythonClient


CONSOLE_SCRIPT = ConsoleScript(
    name="ecosim-client-python",
    description="Runs a Python model in this process for the eCoSim server, with no Pyro5 daemon. "
    + "The [python] section of the config file names the model. Start the server first.",
    examples=("ecosim-client-python --config-file Modules/room/preferences.ini",),
)


@exits_with_one_line_errors(program_name=CONSOLE_SCRIPT.name)
def main(passed_arguments: Sequence[str] | None = None) -> None:
    arguments = CLIArguments(console_script=CONSOLE_SCRIPT, passed_arguments=passed_arguments)
    CONSOLE_SCRIPT.print_banner()
    init_logger(log_level=logging.DEBUG if arguments.debug_enabled() else logging.INFO)
    ShutdownManager().init()

    client = PythonClient.of(
        config_parser=ConfigParser(path=arguments.config_file()),
        config_override=arguments.config_overrides(),
    )
    client.start()
    client.wait_until_finished()

    ShutdownManager().set_shutdown_at_application_end()
    sys.exit(client.exit_code())


if __name__ == "__main__":
    main()
