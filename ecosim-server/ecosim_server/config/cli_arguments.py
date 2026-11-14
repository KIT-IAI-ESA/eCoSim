from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.app_config import AppConfig, AppConfigParameter
from ecosim_common.config.console_script import ConsoleScript
from ecosim_common.config.database_type import DatabaseType
from ecosim_common.config.db_config_overwrite import DbConfigOverwrite
from ecosim_common.config.shared_parameters import COMMUNICATION_PROTOCOL_PARAMETER, DEBUG_PARAMETER
from ecosim_server.config.cli_parameters import CONFIG_FILE_PARAMETERS, IMAGE_RENDERING_PARAMETERS, RUN_PARAMETERS, SERVER_ADDRESS_PARAMETERS
from ecosim_server.config.database_cli_parameters import DATABASE_PARAMETERS

CONSOLE_SCRIPT = ConsoleScript(
    name="ecosim-server",
    description="Runs a simulation. The server waits until every simulator of the simulation config is connected, "
    + "then steps them all and stores the results in files or in PostgreSQL.",
    examples=(
        "ecosim-server --server-config server/preferences.ini --simulation-config server/simulation.json \\\n"
        + "    --steps 100 --database-type file --database-directory results",
        "ecosim-server --server-config server/preferences.ini --simulation-config server/simulation.json \\\n"
        + "    --steps 35040 --step-size 900000 --restore-simulation-run",
    ),
)


class CLIArguments(AppConfig):
    def __init__(
        self,
        passed_arguments: Sequence[str] | None = None,
        console_script: ConsoleScript = CONSOLE_SCRIPT,
    ) -> None:
        super().__init__(
            console_script=console_script,
            parameters=self.parameters(),
            passed_arguments=passed_arguments,
        )

    @classmethod
    def parameters(cls) -> list[AppConfigParameter]:
        return [
            DEBUG_PARAMETER,
            *CONFIG_FILE_PARAMETERS,
            *RUN_PARAMETERS,
            *DATABASE_PARAMETERS,
            *SERVER_ADDRESS_PARAMETERS,
            COMMUNICATION_PROTOCOL_PARAMETER,
            *IMAGE_RENDERING_PARAMETERS,
        ]

    def server_config(self) -> Path:
        path: Path = Path(self._args.server_config)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def simulation_config(self) -> Path:
        path: Path = Path(self._args.simulation_config)
        if path.is_absolute():
            return path
        return Path.cwd() / path

    def simulation_steps(self) -> int:
        return self._args.steps

    def step_size_override(self) -> int | None:
        return self._args.step_size

    def pace(self) -> float:
        return self._args.pace

    def debug_enabled(self) -> bool:
        return self._args.debug

    def image_renderer_port(self) -> int | None:
        return self._args.image_renderer_port

    def image_renderer_interval(self) -> int | None:
        return self._args.image_renderer_interval

    def restore_simulation_run(self) -> bool:
        return self._args.restore_simulation_run

    @property
    def port(self) -> int | None:
        return self._args.port

    def db_config_overwrite(self) -> DbConfigOverwrite:
        return DbConfigOverwrite(
            _host=self._args.database_host,
            _port=self._args.database_port,
            _user=self._args.database_user,
            _user_password=self._args.database_user_password,
            _name=self._args.database_name,
            _schema=self._args.database_schema,
            _ssl=self._args.database_ssl,
            _drop_existing_schema=self._args.database_drop_existing_schema,
            _type=self.database_type(),
            _directory=self.database_directory(),
        )

    def config_overrides(self) -> ServerConfigOverride:
        return ServerConfigOverride(
            server_host=self.host(),
            server_port=self.port,
            communication_protocol=self.communication_protocol(),
        )

    def database_directory(self) -> Path | None:
        if self._args.database_directory is None:
            return None
        return Path(self._args.database_directory)

    def database_type(self) -> DatabaseType | None:
        if self._args.database_type is None:
            return None
        return DatabaseType.of(self._args.database_type)

    def communication_protocol(self) -> CommunicationProtocol | None:
        if self._args.communication_protocol is None:
            return None
        return CommunicationProtocol.of(self._args.communication_protocol)

    def host(self) -> str | None:
        return self._args.host


@dataclass(frozen=True)
class ServerConfigOverride:
    server_host: str | None
    server_port: int | None
    communication_protocol: CommunicationProtocol | None
