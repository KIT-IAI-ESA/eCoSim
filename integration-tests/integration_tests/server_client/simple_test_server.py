from __future__ import annotations

import dataclasses
from datetime import datetime
from enum import Enum
from typing import List

from ecosim_common.config.client_id import ClientID
from ecosim_server.config.server_config import ServerConfig, MainConfig, DatabaseConfig
from ecosim_server.config.simulation_config import SimulationConfig, ClientSimulatorConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_server.server import Server, AbstractServer
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory


@dataclasses.dataclass
class SimpleTestServer(AbstractServer):
    server: Server
    server_config: ServerConfig
    simulation_config: SimulationConfig
    repositories: Repositories

    def start(self) -> None:
        self.server.start()

    def print_measurement_statistics(self) -> None:
        self.server.print_measurement_statistics()

    def force_stop(self) -> None:
        self.server.force_stop()


class RepositoryType(Enum):
    IN_MEMORY = "IN_MEMORY"
    DB = "DB"


def generate_simple_test_server(
    host: str,
    port: int,
    pace: float = 1.0,
    steps: int = 100,
    step_size_in_ms: int = 1_000,
    step_size_in_us: int | None = None,
    simulation_start_date: datetime = datetime(
        year=2025,
        month=1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ),
    repository_type: RepositoryType = RepositoryType.IN_MEMORY,
    clients: List[ClientSimulatorConfig] | None = None,
    database_config: DatabaseConfig | None = None,
    restore_simulation_run: bool = False,
) -> SimpleTestServer:
    clients = clients or [
        ClientSimulatorConfig(
            simulator_name="TestSimulator",
            model_name="TestModel",
            interfaces=[],
            client_id=ClientID(model_name="TestModel", simulator_name="TestSimulator"),
        ),
    ]
    server_config = ServerConfig(
        server=MainConfig(
            host=host,
            port=port,
        ),
        database=database_config or DatabaseConfig(
            host="",
            port=0,
            name="",
            schema="",
            username="",
            password="",
            ssl=False,
            type="",
            drop_existing_schema=False,
        ),
    )
    simulation_config = SimulationConfig(
        clients=clients,
        start_date=simulation_start_date,
        logical_delays=[],
        pace=pace,
        steps=steps,
        step_size_in_ms=step_size_in_ms if step_size_in_us is None else step_size_in_us // 1000,
        step_size_in_us=step_size_in_us,
        restore=restore_simulation_run,
    )
    if repository_type == RepositoryType.DB:
        repositories: Repositories = RepositoriesDB.create(server_config=server_config, simulation_config=simulation_config)
    else:
        repositories: Repositories = RepositoriesInMemory()

    server = Server(
        server_config=server_config,
        simulation_config=simulation_config,
        repositories=repositories,
    )
    return SimpleTestServer(
        server=server,
        server_config=server_config,
        simulation_config=simulation_config,
        repositories=repositories,
    )
