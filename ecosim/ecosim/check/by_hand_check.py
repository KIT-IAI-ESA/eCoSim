"""Ports, which ecosim run sets itself, so they matter only for parts started by hand."""

from pathlib import Path

from ecosim_common.config.config_parser import ConfigParser, ConfigParserException

from ecosim.check.checked_simulator import CheckedSimulator


def by_hand_warnings(server_config_file: Path, simulators: list[CheckedSimulator]) -> list[str]:
    server_config_parser = _config_parser_of(file=server_config_file)
    server_port = _port_of(config_parser=server_config_parser)
    warnings = []
    if server_config_parser is not None and server_port is None:
        warnings.append(f"{server_config_file}: [server] has no port. ecosim run picks one, but ecosim-server started by hand stops without it.")
    for simulator in simulators:
        config_parser = simulator.directory.config_parser
        client_port = _port_of(config_parser=config_parser)
        if client_port is None or not config_parser.contains("server", "ip"):
            warnings.append(
                f"{config_parser.config_file} has no [server] with ip and port. ecosim run gives them to the client, "
                + "but a client started by hand stops without them.",
            )
        elif server_port is not None and client_port != server_port:
            warnings.append(
                f"{config_parser.config_file}: port in [server] is {client_port}, but {server_config_file} has port {server_port}. "
                + "That only matters for a client started by hand.",
            )
    return warnings


def _config_parser_of(file: Path) -> ConfigParser | None:
    try:
        return ConfigParser(file)
    except (OSError, ConfigParserException):
        # the check of the server config names the problem
        return None


def _port_of(config_parser: ConfigParser | None) -> int | None:
    try:
        return None if config_parser is None else config_parser.get_int("server", "port")
    except ConfigParserException:
        return None
