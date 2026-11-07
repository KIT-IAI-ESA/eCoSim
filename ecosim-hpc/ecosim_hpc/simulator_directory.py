from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ecosim_common.client.config.client_config import SimulatorConfig
from ecosim_common.config.client_id import ClientID
from ecosim_common.config.config_parser import ConfigParser
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
        found = SimulatorDirectory._configured_directories_with_a_model_file(simulators_directory=simulators_directory, client_ids=client_ids)
        missing = ", ".join(str(client_id) for client_id in client_ids if client_id not in found)
        if missing:
            raise RuntimeError(
                f"No directory in {simulators_directory} with an ini file and a .py, .fmu or .m file "
                + f"for these simulators (model#simulator): {missing}",
            )
        return found

    @staticmethod
    def _configured_directories_with_a_model_file(simulators_directory: Path, client_ids: list[ClientID]) -> dict[ClientID, SimulatorDirectory]:
        configured: dict[ClientID, SimulatorDirectory] = {}
        for directory in SimulatorDirectory._directories_with_an_ini_file(simulators_directory=simulators_directory):
            if directory.client_id not in client_ids:
                SimulatorDirectory.logger.warning("Skipping %s: the simulation config has no simulator %s.", directory.path, directory.client_id)
            elif directory.client_id in configured:
                raise RuntimeError(
                    f"{configured[directory.client_id].path} and {directory.path} are both for simulator {directory.client_id}, "
                    + "a simulator needs exactly one directory.",
                )
            else:
                configured[directory.client_id] = directory
        return {client_id: directory for client_id, directory in configured.items() if directory.has_a_model_file()}

    @staticmethod
    def _directories_with_an_ini_file(simulators_directory: Path) -> list[SimulatorDirectory]:
        paths = [path for path in simulators_directory.iterdir() if path.is_dir() and any(path.glob("*.ini"))]
        return [SimulatorDirectory._of_path(path) for path in paths]

    @staticmethod
    def _of_path(path: Path) -> SimulatorDirectory:
        ini_files = sorted(ini_file.name for ini_file in path.glob("*.ini"))
        if len(ini_files) > 1:
            raise RuntimeError(f"{path} holds several ini files ({', '.join(ini_files)}), a simulator directory needs exactly one.")
        config_parser = ConfigParser(path / ini_files[0])
        simulator_config = SimulatorConfig.of_config_parser(config_parser)
        client_id = ClientID(model_name=simulator_config.model_name, simulator_name=simulator_config.simulator_name)
        return SimulatorDirectory(path=path, config_parser=config_parser, client_id=client_id)

    def has_a_model_file(self) -> bool:
        return any(any(self.path.glob(pattern)) for pattern in ("*.py", "*.fmu", "*.m"))
