from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ecosim_common.client.config.client_config import SimulatorConfig
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.config_parser import ConfigParser, ConfigParserException
from ecosim_common.tech.logger.logger import ESPLogger


@dataclass(frozen=True)
class SimulatorDirectory:
    logger: ClassVar[ESPLogger] = ESPLogger("SimulatorDirectory")

    path: Path
    config_parser: ConfigParser
    client_id: ClientID

    @staticmethod
    def find_for_simulators(simulators_directory: Path, client_ids: list[ClientID]) -> dict[ClientID, SimulatorDirectory]:
        """Raises before any client starts, naming every simulator that has no directory or no model file in it."""
        search = SimulatorDirectorySearch.of(simulators_directory=simulators_directory, client_ids=client_ids)
        SimulatorDirectory._ensure_every_directory_can_be_used(search=search)
        missing = ", ".join(str(client_id) for client_id in client_ids if client_id not in search.found)
        if missing:
            raise RuntimeError(
                f"No directory in {simulators_directory} with an ini file and a .py, .fmu or .m file "
                + f"for these simulators (model#simulator): {missing}",
            )
        return search.found

    @staticmethod
    def _ensure_every_directory_can_be_used(search: SimulatorDirectorySearch) -> None:
        if search.unreadable:
            raise RuntimeError("\n".join(search.unreadable.values()))
        for directory in search.unconfigured:
            SimulatorDirectory.logger.warning("Skipping %s: the simulation config has no simulator %s.", directory.path, directory.client_id)
        if search.shared:
            client_id, directories = next(iter(search.shared.items()))
            raise RuntimeError(
                f"{directories[0].path} and {directories[1].path} are both for simulator {client_id}, a simulator needs exactly one directory.",
            )

    @staticmethod
    def of_ini_file(ini_file: Path) -> SimulatorDirectory:
        config_parser = ConfigParser(ini_file)
        simulator_config = SimulatorConfig.of_config_parser(config_parser)
        client_id = ClientID(model_name=simulator_config.model_name, simulator_name=simulator_config.simulator_name)
        return SimulatorDirectory(path=ini_file.parent, config_parser=config_parser, client_id=client_id)

    def model_files(self) -> list[Path]:
        return sorted(model_file for pattern in ("*.py", "*.fmu", "*.m") for model_file in self.path.glob(pattern))

    def has_a_model_file(self) -> bool:
        return len(self.model_files()) > 0


@dataclass(frozen=True)
class SimulatorDirectorySearch:
    found: dict[ClientID, SimulatorDirectory]
    unconfigured: list[SimulatorDirectory]
    shared: dict[ClientID, list[SimulatorDirectory]]
    unreadable: dict[Path, str]
    without_model_file: list[SimulatorDirectory]
    missing: list[ClientID]

    @staticmethod
    def of(simulators_directory: Path, client_ids: list[ClientID]) -> SimulatorDirectorySearch:
        paths = [path for path in simulators_directory.iterdir() if path.is_dir() and any(path.glob("*.ini"))]
        directory_or_reason_by_path = {path: SimulatorDirectorySearch._directory_or_reason(path=path) for path in paths}
        return SimulatorDirectorySearch._of_read_directories(
            directories=[directory for directory in directory_or_reason_by_path.values() if isinstance(directory, SimulatorDirectory)],
            unreadable={path: reason for path, reason in directory_or_reason_by_path.items() if isinstance(reason, str)},
            client_ids=client_ids,
        )

    @staticmethod
    def _of_read_directories(
        directories: list[SimulatorDirectory],
        unreadable: dict[Path, str],
        client_ids: list[ClientID],
    ) -> SimulatorDirectorySearch:
        configured = SimulatorDirectorySearch._configured_by_simulator(directories=directories, client_ids=client_ids)
        single_directory_by_simulator = {client_id: candidates[0] for client_id, candidates in configured.items() if len(candidates) == 1}
        return SimulatorDirectorySearch(
            found={client_id: directory for client_id, directory in single_directory_by_simulator.items() if directory.has_a_model_file()},
            unconfigured=[directory for directory in directories if directory.client_id not in client_ids],
            shared={client_id: candidates for client_id, candidates in configured.items() if len(candidates) > 1},
            unreadable=unreadable,
            without_model_file=[directory for directory in single_directory_by_simulator.values() if not directory.has_a_model_file()],
            missing=[client_id for client_id in client_ids if client_id not in configured],
        )

    @staticmethod
    def _directory_or_reason(path: Path) -> SimulatorDirectory | str:
        ini_files = sorted(ini_file.name for ini_file in path.glob("*.ini"))
        if len(ini_files) > 1:
            return f"{path} holds several ini files ({', '.join(ini_files)}), a simulator directory needs exactly one."
        ini_file = path / ini_files[0]
        try:
            return SimulatorDirectory.of_ini_file(ini_file=ini_file)
        except (ConfigParserException, configparser.Error, UnicodeDecodeError, TypeError) as error:
            # the errors of an unknown type or a wrong encoding do not name the file
            return str(error) if str(ini_file) in str(error) else f"{ini_file}: {error}"

    @staticmethod
    def _configured_by_simulator(directories: list[SimulatorDirectory], client_ids: list[ClientID]) -> dict[ClientID, list[SimulatorDirectory]]:
        configured: dict[ClientID, list[SimulatorDirectory]] = {}
        for directory in directories:
            if directory.client_id in client_ids:
                configured.setdefault(directory.client_id, []).append(directory)
        return configured
