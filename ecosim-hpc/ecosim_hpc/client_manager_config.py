from __future__ import annotations

from pathlib import Path

from dataclasses import dataclass

from ecosim_hpc.config.cli_arguments import HPCServerCliArguments
from ecosim_server.config.server_config import ServerConfig


@dataclass(frozen=True)
class ClientManagerConfig:
    host: str
    port: int
    simulator_dir: Path

    @staticmethod
    def of_server_config_and_cli_args(
        server_config: ServerConfig,
        cli_args: HPCServerCliArguments,
    ) -> ClientManagerConfig:
        return ClientManagerConfig(
            host=cli_args.host() or server_config.server.host,
            port=cli_args.port or server_config.server.port,
            simulator_dir=Path(cli_args.simulator_dir()),
        )
