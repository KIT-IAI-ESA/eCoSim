from __future__ import annotations

from dataclasses import dataclass, field

from ecosim_common.tech.parallel.parallel_event import ParallelEvent
from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_server.client.client_message_buffer import ClientMessageBuffer
from ecosim_server.client.client_states import ClientStates
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository


@dataclass
class ServerState(ShutdownListener):
    _simulation_state_repository: SimulationStateRepository = field()
    # TODO_OSR: make field private
    client_states: ClientStates = field()
    _is_finished: ParallelEvent = field()
    _is_interrupted: ParallelEvent = field()
    _is_running: ParallelEvent = field()
    message_buffer: ClientMessageBuffer = field()

    @staticmethod
    def of(
        server_config: ServerConfig,
        simulation_config: SimulationConfig,
        simulation_state_repository: SimulationStateRepository,
    ) -> ServerState:
        return ServerState(
            _simulation_state_repository=simulation_state_repository,
            # TODO_OSR: make field private
            client_states=ClientStates.for_config(
                server_config=server_config,
                simulation_config=simulation_config,
            ),
            _is_finished=ParallelEvent.for_communication_protocol(server_config.server.communication_protocol),
            _is_interrupted=ParallelEvent.for_communication_protocol(server_config.server.communication_protocol),
            _is_running=ParallelEvent.for_communication_protocol(server_config.server.communication_protocol, init_set=True),
            message_buffer=ClientMessageBuffer.for_communication_protocol(server_config.server.communication_protocol),
        )

    def __post_init__(self) -> None:
        ShutdownManager().register_listener(self)

    def wait_for_all_clients_starting_simulation(self) -> None:
        self.client_states.wait_for_all_clients_starting_simulation()

    def have_all_clients_started_simulation(self) -> bool:
        return self.client_states.have_all_clients_started_simulation()

    def have_all_clients_stopped_simulation(self) -> bool:
        return self.client_states.have_all_clients_stopped_simulation()

    def are_all_clients_connected_and_ready(self) -> bool:
        return self.client_states.are_all_clients_connected_and_ready()

    def _update_is_running(self) -> None:
        self._is_running.set_state(not self._is_finished.is_set() and not self._is_interrupted.is_set())

    # callback of ShutdownManager => if this is called the server is interrupted
    def on_app_shutdown(self) -> None:
        self._is_interrupted.set()
        self._update_is_running()
        if self._simulation_state_repository.current() != SimulationState.FINISHED:
            self.set_simulation_state(SimulationState.FAILED)

    def wait_for_all_clients_connected_and_ready(self) -> None:
        self.client_states.wait_for_all_clients_connected_and_ready()

    def set_is_finished(
        self,
        state: bool,
    ) -> None:
        self._is_finished.set_state(state)
        self._update_is_running()
        self.set_simulation_state(SimulationState.FINISHED)

    def set_simulation_state(self, simulation_state: SimulationState) -> None:
        self._simulation_state_repository.update(simulation_state)

    def force_stop(self) -> None:
        self.on_app_shutdown()
        self._is_finished.set()
        self._update_is_running()

    def is_running_event(self) -> ParallelEvent:
        return self._is_running
