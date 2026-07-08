import threading
import dask.distributed as dd
from time import sleep
from typing import Tuple, override

from ecosim_common.communication.channel.connection_address import ConnectionAddress
from ecosim_common.communication.data.client_meta_data import ClientMetaData
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_common.config.client_id import ClientID
from ecosim_server.client_connection import ClientConnection
from ecosim_server.config.simulation_config import SimulationConfig, ClientSimulatorConfig


class ClientState:

    def __init__(
        self,
        client_config: ClientSimulatorConfig,
    ):
        self.client_id: ClientID = client_config.client_id
        self.connection: ClientConnection | None = None
        self.connected: bool = False
        self.interfaces_validated: bool = False
        self.step_size_accepted: bool = False
        self.simulation_started: bool = False
        self.ready_for_simulation: bool = False
        self.stopped_simulation: bool = False

    @property
    def connection_address(self) -> ConnectionAddress | None:
        if not self.connected or self.connection is None:
            return None
        return self.connection.address

    def close_connection(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None
            self.connected = False


class ClientStates(ShutdownListener):
    _logger = ESPLogger("ClientStates")
    thread_lock = threading.Lock()

    def __init__(
        self,
        simulation_config: SimulationConfig,
    ):
        ShutdownManager().register_listener(self)
        self.client_states: dict[ClientID, ClientState] = {}
        for client in simulation_config.clients:
            self.client_states[client.client_id] = ClientState(client)
        self._all_clients_started_simulation_event = threading.Event()
        self._all_clients_ready_for_simulation = threading.Event()
        self._all_clients_stopped_simulation_event = threading.Event()
        self._shutdown_triggered = False

    def add_if_needed(
        self,
        client_config: ClientMetaData,
        client_connection: ClientConnection,
    ) -> bool:
        with ClientStates.thread_lock:
            client = self.client_states.get(client_config.client_id(), None)
            if not client:
                ClientStates._logger.debug(
                    f"Client {client_config.client_id()} ({client_connection.address}) connected but is not needed.",
                )
                return False
            if client.connected:
                ClientStates._logger.debug(
                    f"Client {client_config.client_id()} ({client_connection.address}) connected but " +
                    f"another client ({client.connection_address}) already fulfills this required.",
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
        with ClientStates.thread_lock:
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
        with ClientStates.thread_lock:
            self.client_states[client_id].interfaces_validated = True

    def step_size_accepted(
        self,
        client_id: ClientID,
    ) -> None:
        with ClientStates.thread_lock:
            self.client_states[client_id].step_size_accepted = True

    def simulation_started(
        self,
        client_id: ClientID,
    ) -> None:
        with ClientStates.thread_lock:
            self.client_states[client_id].simulation_started = True
            if all(state.simulation_started for state in self.client_states.values()):
                self._all_clients_started_simulation_event.set()

    def wait_for_all_clients_starting_simulation(self) -> None:
        while not self.have_all_clients_started_simulation():
            sleep(2)
            ClientStates._logger.debug(
                "Waiting for all clients starting simulation: " +
                f"{sum(1 for state in self.client_states.values() if state.simulation_started)}/{len(self.client_states.values())}",
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
        with ClientStates.thread_lock:
            return all((state.connected and state.ready_for_simulation) for state in self.client_states.values())

    def set_client_ready_for_simulation(
        self,
        client_id: ClientID,
    ) -> None:
        with ClientStates.thread_lock:
            self.client_states[client_id].ready_for_simulation = True
            if all(state.ready_for_simulation for state in self.client_states.values()):
                self._all_clients_ready_for_simulation.set()

    def simulation_stopped(
        self,
        client_id: ClientID,
    ) -> None:
        with ClientStates.thread_lock:
            self.client_states[client_id].stopped_simulation = True
            if all((state.stopped_simulation or state.connected is False) for state in self.client_states.values()):
                self._all_clients_stopped_simulation_event.set()

    def wait_for_all_clients_connected_and_ready(self) -> None:
        while not self.are_all_clients_connected_and_ready():
            sleep(2)
            ClientStates._logger.info(
                message="Waiting for all clients to connect: " +
                        f"{
                            sum(
                                1 for state in self.client_states.values()
                                if (state.connected and state.ready_for_simulation)
                            )
                        }/{len(self.client_states.values())}",
            )
            if self._shutdown_triggered:
                raise RuntimeError("Shutdown was triggered during waiting for all clients to start")

    def all_client_ids(self) -> Tuple[ClientID, ...]:
        return tuple(client_state.client_id for client_state in self.client_states.values())


# TODO_AFTER_MERGE: find common abstraction with CLientStates
class ClientStatesDask(ShutdownListener):
    _logger = ESPLogger("ClientStatesDask")

    def __init__(
        self,
        simulation_config: SimulationConfig,
    ):
        self.thread_lock = dd.Lock("client_states")
        ShutdownManager().register_listener(self)
        self.client_states: dict[ClientID, ClientState] = {}
        for client in simulation_config.clients:
            self.client_states[client.client_id] = ClientState(client)
        self._all_clients_started_simulation_event = dd.Event()
        self._all_clients_ready_for_simulation = dd.Event()
        self._all_clients_stopped_simulation_event = dd.Event()
        self._shutdown_triggered = False

    def add_if_needed(
        self,
        client_config: ClientMetaData,
        client_connection: ClientConnection,
    ) -> bool:
        with self.thread_lock:
            client = self.client_states.get(client_config.client_id(), None)
            if not client:
                ClientStatesDask._logger.debug(
                    f"Client {client_config.client_id()} ({client_connection.address}) connected but is not needed.",
                )
                return False
            if client.connected:
                ClientStatesDask._logger.debug(
                    f"Client {client_config.client_id()} ({client_connection.address}) connected but " +
                    f"another client ({client.connection_address}) already fulfills this required.",
                )
                return False
            ClientStatesDask._logger.info(f"Client {client_config.client_id()} ({client_connection.address}) connected.")
            client.connection = client_connection
            client.connected = True
            return True

    def reset_state(
        self,
        client_id: ClientID,
    ) -> None:
        with self.thread_lock:
            ClientStatesDask._logger.debug(f"Resetting client state of {client_id}.")
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
        with self.thread_lock:
            self.client_states[client_id].interfaces_validated = True

    def step_size_accepted(
        self,
        client_id: ClientID,
    ) -> None:
        with self.thread_lock:
            self.client_states[client_id].step_size_accepted = True

    def simulation_started(
        self,
        client_id: ClientID,
    ) -> None:
        with self.thread_lock:
            self.client_states[client_id].simulation_started = True
            if all(state.simulation_started for state in self.client_states.values()):
                self._all_clients_started_simulation_event.set()

    def wait_for_all_clients_starting_simulation(self) -> None:
        while not self.have_all_clients_started_simulation():
            ClientStatesDask._logger.debug(
                "Waiting for all clients starting simulation: " +
                f"{sum(1 for state in self.client_states.values() if state.simulation_started)}/{len(self.client_states.values())}",
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
        with self.thread_lock:
            return all((state.connected and state.ready_for_simulation) for state in self.client_states.values())

    def set_client_ready_for_simulation(
        self,
        client_id: ClientID,
    ) -> None:
        with self.thread_lock:
            self.client_states[client_id].ready_for_simulation = True
            if all(state.ready_for_simulation for state in self.client_states.values()):
                self._all_clients_ready_for_simulation.set()

    def simulation_stopped(
        self,
        client_id: ClientID,
    ) -> None:
        with self.thread_lock:
            self.client_states[client_id].stopped_simulation = True
            if all((state.stopped_simulation or state.connected is False) for state in self.client_states.values()):
                self._all_clients_stopped_simulation_event.set()

    def wait_for_all_clients_connected_and_ready(self) -> None:
        while not self.are_all_clients_connected_and_ready():
            ClientStatesDask._logger.info(
                message="Waiting for all clients to connect: " +
                        f"{
                            sum(
                                1 for state in self.client_states.values()
                                if (state.connected and state.ready_for_simulation)
                            )
                        }/{len(self.client_states.values())}",
            )
            if self._shutdown_triggered:
                raise RuntimeError("Shutdown was triggered during waiting for all clients to start")

    def all_client_ids(self) -> Tuple[ClientID, ...]:
        return tuple(client_state.client_id for client_state in self.client_states.values())
