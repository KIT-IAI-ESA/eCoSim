from dataclasses import dataclass, field
from typing import Callable, Iterable, Tuple, assert_never, override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.tech.structures.esp_map import ESPMap
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.client.client_state import ClientState
from ecosim_server.client.client_connection import ClientConnection
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig


@dataclass
class ClientStates(ShutdownListener):
    _logger = ESPLogger("ClientStates")

    _all_clients_started_simulation_event: ParallelEvent = field()
    _all_clients_ready_for_simulation: ParallelEvent = field()
    _all_clients_stopped_simulation_event: ParallelEvent = field()
    _client_states: ESPMap[ClientID, ClientState] = field()
    _client_ids: Tuple[ClientID, ...] = field()
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
            _client_ids=tuple(init_clients.keys()),
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
                ClientStates._logger.debug("Client %s (%s) connected but is not needed.", client_config.client_id(), client_connection.address)
                return False
            if client.connected:
                ClientStates._logger.debug(
                    "Client %s (%s) connected but another client (%s) already fulfills this required.",
                    client_config.client_id(),
                    client_connection.address,
                    client.connection_address,
                )
                return False
            ClientStates._logger.info("Client %s (%s) connected.", client_config.client_id(), client_connection.address)
            client.connection = client_connection
            client.connected = True
            self._update_events(client_states)
            return True

    def reset_state(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            ClientStates._logger.debug("Resetting client state of %s.", client_id)
            client_states[client_id].close_connection()
            client_states[client_id].connection = None
            client_states[client_id].connected = False
            client_states[client_id].interfaces_validated = False
            client_states[client_id].step_size_accepted = False
            client_states[client_id].simulation_started = False
            client_states[client_id].ready_for_simulation = False
            self._update_events(client_states)

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
            self._update_events(client_states)

    def _log_progress(
        self,
        description: str,
        is_done: Callable[[ClientState], bool],
    ) -> None:
        states = self._client_states.values()
        ClientStates._logger.info(
            "Waiting for all clients %s: %s/%s",
            description,
            sum(1 for state in states if is_done(state)),
            len(states),
        )

    def have_all_clients_started_simulation(self) -> bool:
        return self._all_clients_started_simulation_event.is_set()

    def have_all_clients_stopped_simulation(self) -> bool:
        return self._all_clients_stopped_simulation_event.is_set()

    @override
    def on_app_shutdown(self) -> None:
        self._shutdown_triggered = True

    def is_connected(
        self,
        client_id: ClientID,
    ) -> bool:
        client_state = self._client_states.value_of(client_id)
        return client_state is not None and client_state.connected

    def are_all_clients_connected_and_ready(self) -> bool:
        with self._client_states.transaction() as client_states:
            return all((state.connected and state.ready_for_simulation) for state in client_states.values())

    def lost_client_ids(
        self,
        client_ids: Iterable[ClientID],
    ) -> Tuple[ClientID, ...]:
        states = self._client_states.get_snapshot()
        return tuple(client_id for client_id in client_ids if not (states[client_id].connected and states[client_id].ready_for_simulation))

    def set_client_ready_for_simulation(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].ready_for_simulation = True
            self._update_events(client_states)

    def simulation_stopped(
        self,
        client_id: ClientID,
    ) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].stopped_simulation = True
            client_states[client_id].connected = False
            self._update_events(client_states)

    def wait_for_all_clients_connected_and_ready(self) -> None:
        self._all_clients_ready_for_simulation.wait_with_progress(
            progress_interval_in_seconds=1.0,
            on_progress=lambda: self._log_progress("to connect", lambda state: state.connected and state.ready_for_simulation),
            abort=lambda: self._shutdown_triggered,
            abort_message="Shutdown was triggered during waiting for all clients to connect",
        )

    def all_client_ids(self) -> Tuple[ClientID, ...]:
        return self._client_ids

    def all_connections(self) -> Tuple[ClientConnection | None, ...]:
        return tuple(client_state.connection for client_state in self._client_states.values())

    def all_states(self) -> Tuple[ClientState, ...]:
        return tuple(self._client_states.values())

    def get_connection_for(self, client_id: ClientID) -> ClientConnection | None:
        client_state = self._client_states.value_of(client_id)
        return client_state.connection if client_state is not None else None

    def set_client_connected_state(self, client_id: ClientID, connected: bool) -> None:
        with self._client_states.transaction() as client_states:
            client_states[client_id].connected = connected
            self._update_events(client_states)

    def _update_events(self, client_states: dict[ClientID, ClientState]) -> None:
        states = tuple(client_states.values())
        self._all_clients_started_simulation_event.set_state(all(state.simulation_started for state in states))
        self._all_clients_ready_for_simulation.set_state(all((state.connected and state.ready_for_simulation) for state in states))
        self._all_clients_stopped_simulation_event.set_state(all((state.stopped_simulation or not state.connected) for state in states))
