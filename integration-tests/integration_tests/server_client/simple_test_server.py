from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_states import ClientStates
from ecosim_server.config.server_config import DatabaseConfig, MainConfig, ServerConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.data.repositories import Repositories
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_server.server import Server
from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory


@dataclass
class SimpleTestServer(Server):
    server: Server = field()

    def start(self) -> None:
        self.server.start()

    def print_measurement_statistics(self) -> None:
        self.server.print_measurement_statistics()

    def force_stop(self) -> None:
        self.server.force_stop()

    def measurement_repository(self, client_id: ClientID) -> MeasurementRepository:
        return self._repositories.measurement_repository(client_id=client_id)

    def step_to_date(self, step: int) -> datetime:
        return self._simulation_config.date_time_for_step(step)

    def date_to_step(self, date: datetime) -> int:
        return self._simulation_config.date_time_to_step(date)

    def client_communication(self) -> ClientCommunication:
        return self.server._simulation_executor._client_communication  # noqa: SLF001

    def start_and_wait_for_all_clients_connected_and_ready(self) -> None:
        self.server._start_listening()  # noqa: SLF001
        self.server._wait_for_all_clients_connected_and_ready()  # noqa: SLF001

    def client_states(self) -> ClientStates:
        return self.client_communication()._client_states  # noqa: SLF001

    def communication_protocol(self) -> CommunicationProtocol:
        return self.server._server_config.server.communication_protocol  # noqa: SLF001


class RepositoryType(Enum):
    IN_MEMORY = "IN_MEMORY"
    DB = "DB"


@dataclass
class SimpleTestServerParameters:
    communication_protocol: CommunicationProtocol
    host: str
    port: int
    pace: float = field(default=1.0)
    steps: int = field(default=100)
    step_size_in_ms: int = field(default=1_000)
    simulation_start_date: datetime = field(
        default_factory=lambda: datetime(
            year=2025,
            month=1,
            day=1,
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        ),
    )
    repository_type: RepositoryType = field(default=RepositoryType.IN_MEMORY)
    clients: List[ClientSimulatorConfig] | None = field(default=None)
    database_config: DatabaseConfig | None = field(default=None)
    restore_simulation_run: bool = field(default=False)


def generate_simple_test_server(parameters: SimpleTestServerParameters) -> SimpleTestServer:
    clients = parameters.clients or [
        ClientSimulatorConfig(
            simulator_name="TestSimulator",
            model_name="TestModel",
            interfaces=[],
            client_id=ClientID(model_name="TestModel", simulator_name="TestSimulator"),
        ),
    ]
    server_config = ServerConfig(
        server=MainConfig(
            host=parameters.host,
            port=parameters.port,
            communication_protocol=parameters.communication_protocol,
        ),
        database=parameters.database_config
        or DatabaseConfig(
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
        start_date=parameters.simulation_start_date,
        logical_delays=[],
        pace=parameters.pace,
        steps=parameters.steps,
        step_size_in_ms=parameters.step_size_in_ms,
        restore=parameters.restore_simulation_run,
    )
    repositories: Repositories
    if parameters.repository_type == RepositoryType.DB:
        repositories = RepositoriesDB.create(server_config=server_config, simulation_config=simulation_config)
    else:
        repositories = RepositoriesInMemory.for_communication_protocol(server_config.server.communication_protocol)

    server: Server = Server(
        _server_config=server_config,
        _simulation_config=simulation_config,
        _repositories=repositories,
    )

    return SimpleTestServer(
        server=server,
        _server_config=server_config,
        _simulation_config=simulation_config,
        _repositories=repositories,
    )
