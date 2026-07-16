from dataclasses import dataclass, field
from time import sleep
from typing import Tuple, assert_never, override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.config.client_id import ClientID
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.dask_dictionary_for_simple_objects import DaskDictionaryForSimpleObjects
from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_server.client.client_state import ClientState
from ecosim_server.client_connection import ClientConnection
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig


@dataclass
class ClientStates(ShutdownListener):
    _logger = ESPLogger("ClientStates")

    _parallel_lock: ParallelLock = field()
    _all_clients_started_simulation_event: ParallelEvent = field()
    _all_clients_ready_for_simulation: ParallelEvent = field()
    _all_clients_stopped_simulation_event: ParallelEvent = field()
    # TODO_OSR: make this field private
    client_states: dict[ClientID, ClientState] | DaskDictionaryForSimpleObjects[ClientID, ClientState] = field()
    _shutdown_triggered: bool = field(default=False)

    @staticmethod
    def for_config(
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
    ) -> "ClientStates":
        client_states: dict[ClientID, ClientState] | DaskDictionaryForSimpleObjects[ClientID, ClientState] = {
            client.client_id: ClientState(client) for client in simulation_config.clients
        }

        match server_config.server.communication_protocol:
            case CommunicationProtocol.DASK:
                client_states = DaskDictionaryForSimpleObjects(name="client_states", default=client_states)
            case CommunicationProtocol.TCP_SOCKET:
                pass
            case _:
                assert_never(server_config.server.communication_protocol)

        return ClientStates(
            _parallel_lock=ParallelLock.for_protocol(
                communication_protocol=server_config.server.communication_protocol,
                dask_lock_name="client_states",
            ),
            client_states=client_states,
            _all_clients_started_simulation_event=ParallelEvent.for_communication_protocol(server_config.server.communication_protocol),
            _all_clients_ready_for_simulation=ParallelEvent.for_communication_protocol(server_config.server.communication_protocol),
            _all_clients_stopped_simulation_event=ParallelEvent.for_communication_protocol(server_config.server.communication_protocol),
        )

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    def add_if_needed(
        self,
        client_config: ClientMetaData,
        client_connection: ClientConnection,
    ) -> bool:
        with self._parallel_lock:
            client = self.client_states.get(client_config.client_id(), None)
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
        with self._parallel_lock:
            ClientStates._logger.debug(f"Resetting client state of {client_id}.")
            self.client_states[client_id].close_connection()
            self.client_states[client_id].connection = None
            self.client_states[client_id].connected = False
            self.client_states[client_id].interfaces_validated = False
            self.client_states[client_id].step_size_accepted = False
            self.client_states[client_id].simulation_started = False
            self.client_states[client_id].ready_for_simulation = False

    def interfaces_validated(
        self,
        client_id: ClientID,
    ) -> None:
        with self._parallel_lock:
            self.client_states[client_id].interfaces_validated = True

    def step_size_accepted(
        self,
        client_id: ClientID,
    ) -> None:
        with self._parallel_lock:
            self.client_states[client_id].step_size_accepted = True

    def simulation_started(
        self,
        client_id: ClientID,
    ) -> None:
        with self._parallel_lock:
            self.client_states[client_id].simulation_started = True
            if all(state.simulation_started for state in self.client_states.values()):
                self._all_clients_started_simulation_event.set()

    def wait_for_all_clients_starting_simulation(self) -> None:
        while not self.have_all_clients_started_simulation():
            # TODO_OSR: replace sleep with a correct async/threading construct
            sleep(1)
            # TODO_OSR: check if the 'sum' function can be refactored (also check the similar todo)
            ClientStates._logger.debug(
                "Waiting for all clients starting simulation: "
                + f"{sum(1 for state in self.client_states.values() if state.simulation_started)}/{len(self.client_states.values())}",
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
        return self.client_states[client_id] is not None and self.client_states[client_id].connected

    def are_all_clients_connected_and_ready(self) -> bool:
        with self._parallel_lock:
            return all((state.connected and state.ready_for_simulation) for state in self.client_states.values())

    def set_client_ready_for_simulation(
        self,
        client_id: ClientID,
    ) -> None:
        with self._parallel_lock:
            self.client_states[client_id].ready_for_simulation = True
            if all(state.ready_for_simulation for state in self.client_states.values()):
                self._all_clients_ready_for_simulation.set()

    def simulation_stopped(
        self,
        client_id: ClientID,
    ) -> None:
        with self._parallel_lock:
            self.client_states[client_id].stopped_simulation = True
            if all((state.stopped_simulation or state.connected is False) for state in self.client_states.values()):
                self._all_clients_stopped_simulation_event.set()

    def wait_for_all_clients_connected_and_ready(self) -> None:
        while not self.are_all_clients_connected_and_ready():
            # TODO_OSR: replace sleep with a correct async/threading construct
            sleep(1)
            # TODO_OSR: check if the 'sum' function can be refactored (also check the similar todo)
            ClientStates._logger.info(
                message="Waiting for all clients to connect: "
                + f"{sum(1 for state in self.client_states.values() if (state.connected and state.ready_for_simulation))}/{
                    len(self.client_states.values())
                }",
            )
            if self._shutdown_triggered:
                raise RuntimeError("Shutdown was triggered during waiting for all clients to start")

    def all_client_ids(self) -> Tuple[ClientID, ...]:
        return tuple(client_state.client_id for client_state in self.client_states.values())
