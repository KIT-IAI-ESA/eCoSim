from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.config.client_id import ClientID
from ecosim_server.client.client_communication import ClientCommunication
from ecosim_server.client.client_states import ClientStates
from ecosim_server.config.server_config import DatabaseConfig, MainConfig, ServerConfig
from ecosim_server.config.simulation_config import ClientSimulatorConfig, SimulationConfig
from ecosim_server.data.repositories import Repositories, create_repositories
from ecosim_server.measurement.measurement_repository import MeasurementRepository
from ecosim_server.server import Server
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository
from ecosim_test_common.timeouts import WAIT_TIMEOUT_IN_SECONDS

from integration_tests.tech.db.repositories_in_memory import RepositoriesInMemory
from integration_tests.test_data.server_client.simple_test_server_parameters import SimpleTestServerParameters

# below the per-test 'timeout' in pyproject.toml, so a hang fails here with a message and not at that limit
SERVER_FINISH_TIMEOUT_IN_SECONDS = 110


@dataclass
class SimpleTestServer(Server):
    _thread: threading.Thread | None = field(init=False, default=None)

    def measurement_repository(self, client_id: ClientID) -> MeasurementRepository:
        return self._repositories.measurement_repository(client_id=client_id)

    def simulation_state_repository(self) -> SimulationStateRepository:
        return self._repositories.simulation_state_repository

    def step_to_date(self, step: int) -> datetime:
        return self._simulation_config.date_time_for_step(step)

    def date_to_step(self, date: datetime) -> int:
        return self._simulation_config.date_time_to_step(date)

    def client_communication(self) -> ClientCommunication:
        return self._simulation_executor._client_communication  # noqa: SLF001

    def start_in_thread(self) -> None:
        self._thread = threading.Thread(target=self.start, daemon=True)
        self._thread.start()

    def assert_finishing_in_time(self, timeout_in_seconds: float = SERVER_FINISH_TIMEOUT_IN_SECONDS) -> None:
        assert self._thread is not None, "The server was not started in the background"
        self._thread.join(timeout=timeout_in_seconds)
        assert not self._thread.is_alive(), f"The server did not finish within {timeout_in_seconds}s"

    def start_and_wait_for_all_clients_connected_and_ready(self) -> None:
        self._start_listening()
        self._wait_for_all_clients_connected_and_ready()

    def wait_until_listening(self, timeout_in_seconds: float = WAIT_TIMEOUT_IN_SECONDS) -> None:
        listening = self._channel.is_listening_on_connection_event().wait(timeout=timeout_in_seconds)
        assert listening, f"The server did not listen within {timeout_in_seconds}s"

    def client_states(self) -> ClientStates:
        return self.client_communication()._client_states  # noqa: SLF001

    def communication_protocol(self) -> CommunicationProtocol:
        return self._server_config.server.communication_protocol  # noqa: SLF001


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
            drop_existing_schema=False,
        ),
    )
    simulation_config = SimulationConfig(
        clients=clients,
        start_date=parameters.simulation_start_date,
        logical_delays=parameters.logical_delays,
        pace=parameters.pace,
        steps=parameters.steps,
        step_size_in_ms=parameters.step_size_in_ms,
        restore=parameters.restore_simulation_run,
    )
    repositories: Repositories
    if parameters.database_config is None:
        # without a database there is nothing to store in, so the test runs on the in memory repositories
        repositories = RepositoriesInMemory.for_communication_protocol(server_config.server.communication_protocol)
    else:
        # the production implementations are picked by the database type, exactly like 'main.py' picks them
        repositories = create_repositories(server_config=server_config, simulation_config=simulation_config)

    return SimpleTestServer(
        _server_config=server_config,
        _simulation_config=simulation_config,
        _repositories=repositories,
        _response_timeouts=parameters.response_timeouts,
    )
