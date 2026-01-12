from importlib.metadata import version
import logging
import tomllib
from pathlib import Path
from time import sleep
from art import tprint

from ecosim_client_pyro5.pyro_client import PyroClient
from ecosim_common.client.config.cli_arguments import CLIArguments

from ecosim_common.config import config_parser
from ecosim_common.tech.logger.logger import ESPLogger, init_logger
from ecosim_common.tech.shutdown_manager import ShutdownManager


def get_version() -> str:
    # noinspection PyBroadException
    try:
        return version("ecosim-client-pyro5")
    except Exception:
        pass
    pyproject_path = Path("../pyproject.toml")
    # Packaging into .exe via Pyinstaller does not find the right toml to open
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        return pyproject_data["project"]["version"]
    except FileNotFoundError:
        return "1.0"


def main():
    tprint("eCoSimPy", font="tarty1", chr_ignore=True)
    print(f"Pyro Client - {get_version()}")
    sleep(0.5)
    args = CLIArguments()

    ShutdownManager().init()
    init_logger(log_level=logging.DEBUG if args.debug_enabled() else logging.INFO)

    main_logger = ESPLogger("main")

    config = config_parser.ConfigParser(args.config_file())
    client = PyroClient(config, args.config_overrides())
    main_logger.debug("Calling client.connect()")
    client.start()
    client.wait_until_finished()
    main_logger.debug("Reached end")

    ShutdownManager().set_shutdown_at_application_end()


if __name__ == '__main__':
    main()
