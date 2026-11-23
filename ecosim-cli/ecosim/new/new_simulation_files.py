from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from ecosim_common.client.config.client_config import ClientInterfaceConfig, ServerConfig, SimpleClientConfig, SimulatorConfig
from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.database_type import DatabaseType
from ecosim_common_fmpy.config.fmu_base_config import FMUBaseConfig
from ecosim_common_fmpy.config.fmu_interfaces import FMUInterface
from ecosim_server.measurement.postgres_name_check import MAXIMUM_SIMULATOR_NAME_IN_BYTES

from ecosim.new.new_simulation_config import NewSimulationConfig
from ecosim.new.simulation_model import SimulationModel
from ecosim.simulation_directory import SimulationDirectory


@dataclass(frozen=True)
class NewSimulationFiles:
    """Writes the files into a draft folder and moves them into place at the end."""

    port: int
    database_type: DatabaseType
    database_directory: str

    def write(self, simulation: SimulationDirectory, models: list[SimulationModel], new_simulation_config: NewSimulationConfig) -> None:
        if self.database_type is DatabaseType.POSTGRES:
            _ensure_the_names_fit_postgres(models=models)
        target = simulation.path.absolute()
        draft = _new_draft_for(target=target)
        try:
            for model in models:
                self._write_model(directory=draft.simulator_dir / model.name, model=model)
            draft.simulation_config.parent.mkdir()
            draft.simulation_config.write_text(new_simulation_config.as_json(), encoding="utf-8")
            draft.server_config.write_text(self._server_config_content(), encoding="utf-8")
            _move_into_place(draft=draft.path, target=target)
        except BaseException:
            # BaseException to clean up after a Ctrl-C too
            shutil.rmtree(draft.path, ignore_errors=True)
            raise

    def _write_model(self, directory: Path, model: SimulationModel) -> None:
        directory.mkdir(parents=True)
        shutil.copyfile(src=model.interfaces.fmu_file, dst=directory / f"{model.name}.fmu")
        interfaces = {"inputs": _fmc_entries(interfaces=model.interfaces.inputs), "outputs": _fmc_entries(interfaces=model.interfaces.outputs)}
        (directory / f"{model.name}.fmc").write_text(json.dumps(interfaces, indent=2) + "\n", encoding="utf-8")
        (directory / "preferences.ini").write_text(self._client_config_content(model=model) + "\n", encoding="utf-8")

    def _client_config_content(self, model: SimulationModel) -> str:
        return SimpleClientConfig(
            _server_config=ServerConfig(
                server_address=ConnectionAddress(ip="localhost", port=self.port),
                communication_protocol=CommunicationProtocol.TCP_SOCKET,
            ),
            _simulator_config=SimulatorConfig(
                simulator_name=model.name,
                model_name=model.name,
                fmc_file=f"{model.name}.fmc",
                type=model.interfaces.client_type(),
            ),
            _interfaces_config=ClientInterfaceConfig(interfaces=[]),
            _extra_sections=[FMUBaseConfig(fmu_file=Path(f"{model.name}.fmu")).as_string()],
        ).as_config_file_content()

    def _server_config_content(self) -> str:
        lines = ["[server]", "host = localhost", f"port = {self.port}", "", "[database]", f"type = {self.database_type.serialized}"]
        if self.database_type is DatabaseType.FILE:
            return "\n".join([*lines, f"directory = {self.database_directory}", ""])
        # the password comes from PGPASSWORD or the password file
        return "\n".join([*lines, "server = localhost", "port = 5432", "username =", "ssl = false", ""])


def ensure_the_directory_is_new(simulation: SimulationDirectory) -> None:
    if simulation.path.is_file():
        raise ValueError(f"{simulation.path} is a file. Use the name of a new folder for the simulation.")
    if simulation.path.is_dir() and any(simulation.path.iterdir()):
        raise ValueError(f"{simulation.path} already exists and is not empty. Choose a new folder, or delete this one first.")


def _fmc_entries(interfaces: tuple[FMUInterface, ...]) -> list[dict[str, str]]:
    return [{"name": interface.name, "unit": interface.unit, "description": interface.description} for interface in interfaces]


def _new_draft_for(target: Path) -> SimulationDirectory:
    # the folder around an empty simulation folder may not be writable
    draft_parent = target if target.is_dir() else target.parent
    draft_parent.mkdir(parents=True, exist_ok=True)
    # tempfile would ignore the umask
    draft = SimulationDirectory.of_path(path=draft_parent / f".{target.name}-{uuid4().hex[:8]}")
    draft.path.mkdir()
    return draft


def _ensure_the_names_fit_postgres(models: list[SimulationModel]) -> None:
    for model in models:
        if len(model.name) > MAXIMUM_SIMULATOR_NAME_IN_BYTES:
            raise ValueError(
                f"The model name {model.name} has {len(model.name)} characters, but PostgreSQL takes at most {MAXIMUM_SIMULATOR_NAME_IN_BYTES}. "
                + f"Use a shorter name, like {model.name[:16]}={model.interfaces.fmu_file}",
            )


def _move_into_place(draft: Path, target: Path) -> None:
    if draft.parent != target:
        draft.rename(target)
        return
    # the empty folder stays, it may be the current folder of a shell
    for entry in draft.iterdir():
        entry.rename(target / entry.name)
    draft.rmdir()
