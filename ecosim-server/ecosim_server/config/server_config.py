from __future__ import annotations

from pathlib import Path

from dataclasses import dataclass, field
from typing import ClassVar

from sqlalchemy import URL

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.config_parser import ConfigParser
from ecosim_common.config.db_config_overwrite import DbConfigOverwrite
from ecosim_common.tech.logger.global_logger import GlobalLogger
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.optional_access import if_exists
from ecosim_server.config.cli_arguments import CLIArguments, ServerConfigOverride
from ecosim_common.config.database_type import DatabaseType


@dataclass(frozen=True)
class ServerConfig:
    _protocol_version: ClassVar[str] = "2.0"
    logger: ClassVar[ESPLogger] = ESPLogger("ServerConfig")

    server: MainConfig
    database: DatabaseConfig

    @staticmethod
    def of_cli_args(args: CLIArguments) -> ServerConfig:
        return ServerConfig.of_file(
            file=args.server_config(),
            config_override=args.config_overrides(),
            image_renderer_port=args.image_renderer_port(),
            image_renderer_interval=args.image_renderer_interval(),
            db_config_overwrite=args.db_config_overwrite(),
        )

    @staticmethod
    def of_file(
        file: Path,
        config_override: ServerConfigOverride = ServerConfigOverride(
            server_host=None,
            server_port=None,
            communication_protocol=None,
        ),
        image_renderer_port: int | None = None,
        image_renderer_interval: int | None = None,
        db_config_overwrite: DbConfigOverwrite = DbConfigOverwrite(),
    ) -> ServerConfig:
        config = ConfigParser(file)
        return ServerConfig(
            server=MainConfig.of_config_parser(
                config_parser=config,
                config_override=config_override,
                image_renderer_port=image_renderer_port,
                image_renderer_interval=image_renderer_interval,
            ),
            database=DatabaseConfig.from_config(config, db_config_overwrite),
        )

    def print_config_for_start_up(self) -> None:
        GlobalLogger.print_values(
            header="SERVER CONFIG",
            value_pairs={
                "Server address": f"{self.server.host}:{self.server.port}",
                "Image renderer socket": f"{f'{self.server.host}:{self.server.image_renderer_port}' if self.server.image_renderer_port else 'N/A'}",
                "Image renderer interval": f"{self.server.image_renderer_interval if self.server.image_renderer_interval else 'N/A'}",
                "Database server": f"{self.database.host}:{self.database.port} ({self.database.type.value})",
                "Database name": self.database.name,
                "Database schema": self.database.schema,
                "Database directory": self.database.directory,
            },
        )


@dataclass(frozen=True)
class MainConfig:
    host: str
    port: int
    communication_protocol: CommunicationProtocol
    image_renderer_port: int | None = None
    image_renderer_interval: int | None = None

    @staticmethod
    def of_config_parser(
        config_parser: ConfigParser,
        config_override: ServerConfigOverride = ServerConfigOverride(
            server_host=None,
            server_port=None,
            communication_protocol=None,
        ),
        image_renderer_port: int | None = None,
        image_renderer_interval: int | None = None,
    ) -> MainConfig:
        return MainConfig(
            port=MainConfig._get_port(config_parser, config_override),
            host=config_override.server_host or config_parser.get_string("server", "host", default="localhost"),
            communication_protocol=(
                if_exists(config_override).communication_protocol
                or config_parser.get_enum(CommunicationProtocol, "server", "communication_protocol", CommunicationProtocol.TCP_SOCKET)
            ),
            image_renderer_port=image_renderer_port,
            image_renderer_interval=image_renderer_interval,
        )

    @staticmethod
    def _get_port(
        config: ConfigParser,
        config_override: ServerConfigOverride,
    ) -> int:
        # This method is mainly responsible for getting a meaningful info log if the port is overridden
        if config.contains("server", "port") and config_override.server_port is not None:
            config_port = config.get_int("server", "port")
            ServerConfig.logger.info(
                "Port was passed as an CLI argument. The port in the config file (%s) is therefor overridden with %s",
                config_port,
                config_override.server_port,
            )
            return config_override.server_port
        if config_override.server_port is not None:
            return config_override.server_port
        if config.contains("server", "port"):
            return config.get_int("server", "port")
        raise Exception(
            "Server port is neither provided by CLI args nor by config file.",
        )

    def connection_address(self) -> ConnectionAddress:
        return ConnectionAddress(
            ip=self.host,
            port=self.port,
        )


@dataclass(frozen=True)
class DatabaseConfig:
    _default_directory: ClassVar[Path] = Path("simulation_results")
    _maintenance_database: ClassVar[str] = "postgres"

    host: str
    port: int
    ssl: bool
    drop_existing_schema: bool
    username: str
    password: str = field(repr=False)
    schema: str
    name: str = "sim_control"
    type: DatabaseType = DatabaseType.POSTGRES
    directory: Path = _default_directory

    @classmethod
    def from_config(
        cls,
        config: ConfigParser,
        db_overwrite: DbConfigOverwrite = DbConfigOverwrite(),
    ) -> DatabaseConfig:
        return cls(
            host=db_overwrite.host(default=config.get_string("database", "server")),
            port=db_overwrite.port(read_default=lambda: config.get_int("database", "port")),
            ssl=db_overwrite.ssl(default=config.get_bool("database", "ssl")),
            name=db_overwrite.name(default="sim_control"),
            schema=db_overwrite.schema(default="sim_control"),
            username=db_overwrite.user(
                default=config.get_string("database", "username"),
            ),
            password=db_overwrite.user_password(
                default=config.get_string("database", "password", default=""),
            ),
            drop_existing_schema=db_overwrite.drop_existing_schema(False),
            type=db_overwrite.type(default=DatabaseType.of(config.get_string("database", "type", DatabaseType.POSTGRES.value))),
            directory=db_overwrite.directory(default=Path(config.get_string("database", "directory", DatabaseConfig._default_directory.name))),
        )

    def generate_sqlalchemy_db_url(self) -> URL:
        return self._url_of(self.name)

    def generate_sqlalchemy_root_url(self) -> URL:
        return self._url_of(DatabaseConfig._maintenance_database)

    def _url_of(self, database: str) -> URL:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.username,
            # without a password, libpq looks in PGPASSWORD and the password file
            password=self.password or None,
            host=self.host,
            port=self.port,
            database=database,
            query={"sslmode": "require" if self.ssl else "disable"},
        )
