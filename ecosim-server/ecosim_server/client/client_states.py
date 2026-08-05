from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, assert_never, override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.client.client_state import ClientState
from ecosim_server.client_connection import ClientConnection
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig


@dataclass
class ClientStates(ShutdownListener):
    _logger = ESPLogger("ClientStates")

    _all_clients_started_simulation_event: ParallelEvent = field()
    _all_clients_ready_for_simulation: ParallelEvent = field()
    _all_clients_stopped_simulation_event: ParallelEvent = field()
    _client_states: ESPMap[ClientID, ClientState] = field()
    _shutdown_triggered: bool = field(default=False)

    @staticmethod
    def for_config(
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
    ) -> "ClientStates":
        return ClientStates._for_clients_and_protocol(
            communication_protocol=server_config.server.communication_protocol,
            init_clients={client.client_id: ClientState.of_client_config(client) for client in simulation_config.clients},
        )

    @staticmethod
    def _for_clients_and_protocol(
        communication_protocol: CommunicationProtocol,
        init_clients: dict[ClientID, ClientState],
    ) -> "ClientStates":
        match communication_protocol:
            case CommunicationProtocol.DASK:
                client_states = ESPMap.of_type(
                    ESPStructureType.DASK_VARIABLE,
                    dask_name="client_states",
                    data=init_clients,
                )
            case CommunicationProtocol.TCP_SOCKET:
                client_states = ESPMap.of_type(
                    ESPStructureType.THREAD,
                    data=init_clients,
                )
            case _:
                assert_never(communication_protocol)

        return ClientStates(
            _client_states=client_states,
            _all_clients_started_simulation_event=ParallelEvent.for_communication_protocol(communication_protocol),
            _all_clients_ready_for_simulation=ParallelEvent.for_communication_protocol(communication_protocol),
            _all_clients_stopped_simulation_event=ParallelEvent.for_communication_protocol(communication_protocol),
        )

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    def add_if_needed(
        self,
        client_config: ClientMetaData,
        client_connection: ClientConnection,
    ) -> bool:
        with self._client_states.transaction() as client_states:
            client = client_states.get(client_config.client_id(), None)
            if not client:
                ClientStates._logger.debug(
                    f"Client {client_config.client_id()} ({client_connection.address}) connected but is not needed.",
                )
                return False
            if client.connected:
                ClientStates._logger.debug(
                    f"Client {client_config.client_id()} ({client_connection.address}) connected but "
                    + f"another client ({client.connection_address}) already fulfills this required.",
                )
                return False
            ClientStates._logger.info(f"Client {client_config.client_id()} ({client_connection.address}) connected.")
            client.connection = client_connection
            client.connected = True
            return True

    def reset_state(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            ClientStates._logger.debug(f"Resetting client state of {client_id}.")
            client_states[client_id].close_connection()
            client_states[client_id].connection = None
            client_states[client_id].connected = False
            client_states[client_id].interfaces_validated = False
            client_states[client_id].step_size_accepted = False
            client_states[client_id].simulation_started = False
            client_states[client_id].ready_for_simulation = False

    def interfaces_validated(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].interfaces_validated = True

    def step_size_accepted(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].step_size_accepted = True

    def simulation_started(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].simulation_started = True
            if all(state.simulation_started for state in client_states.values()):
                self._all_clients_started_simulation_event.set()

    def wait_for_all_clients_starting_simulation(self) -> None:
        while not self.have_all_clients_started_simulation():
            # TODO_OSR: replace sleep with a correct async/threading construct
            sleep(1)
            # TODO_OSR: check if the 'sum' function can be refactored (also check the similar todo)
            ClientStates._logger.debug(
                "Waiting for all clients starting simulation: "
                + f"{sum(1 for state in self._client_states.values() if state.simulation_started)}/{len(self._client_states.values())}",
            )
            if self._shutdown_triggered:
                raise RuntimeError("Shutdown was triggered during waiting for all clients to start")

    def have_all_clients_started_simulation(self) -> bool:
        return self._all_clients_started_simulation_event.is_set()

    def have_all_clients_stopped_simulation(self) -> bool:
        return self._all_clients_stopped_simulation_event.is_set()

    def are_all_clients_ready_for_simulation(self) -> bool:
        return self._all_clients_ready_for_simulation.is_set()

    @override
    def on_app_shutdown(self) -> None:
        self._shutdown_triggered = True

    def is_connected(
        self,
        client_id: ClientID,
    ) -> bool:
        return self._client_states[client_id] is not None and self._client_states[client_id].connected

    def are_all_clients_connected_and_ready(self) -> bool:
        with self._client_states.transaction() as client_states:
            return all((state.connected and state.ready_for_simulation) for state in client_states.values())

    def set_client_ready_for_simulation(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].ready_for_simulation = True
            if all(state.ready_for_simulation for state in client_states.values()):
                self._all_clients_ready_for_simulation.set()

    def simulation_stopped(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].stopped_simulation = True
            client_states[client_id].connected = False
            if all((state.stopped_simulation or state.connected is False) for state in client_states.values()):
                self._all_clients_stopped_simulation_event.set()

    # TODO_OSR: after the refactoring, you can probably delete this
    def wait_for_all_clients_connected_and_ready(self) -> None:
        while not self.are_all_clients_connected_and_ready():
            # TODO_OSR: replace sleep with a correct async/threading construct
            sleep(1)
            # TODO_OSR: check if the 'sum' function can be refactored (also check the similar todo)
            ClientStates._logger.info(
                message="Waiting for all clients to connect: "
                + f"{sum(1 for state in self._client_states.values() if (state.connected and state.ready_for_simulation))}/{
                    len(self._client_states.values())
                }",
            )
            if self._shutdown_triggered:
                raise RuntimeError("Shutdown was triggered during waiting for all clients to start")

    def all_client_ids(self) -> Tuple[ClientID, ...]:
        return tuple(client_state.client_id for client_state in self._client_states.values())

    def all_connections(self) -> Tuple[ClientConnection | None, ...]:
        return tuple(client_state.connection for client_state in self._client_states.values())

    def all_states(self) -> Tuple[ClientState, ...]:
        return tuple(self._client_states.values())

    def get_connection_for(self, client_id: ClientID) -> ClientConnection | None:
        return self._client_states[client_id].connection

    def set_client_connected_state(self, client_id: ClientID, connected: bool) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].connected = connected
