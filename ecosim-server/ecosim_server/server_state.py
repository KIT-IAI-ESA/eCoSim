from dask.distributed import get_client

from ecosim_common.tech.shutdown_manager import ShutdownListener, ShutdownManager
from ecosim_server.client.client_state import ClientStates, ClientStatesDask
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement
from ecosim_server.message_buffer import ClientMessageBuffer
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository


class ServerState(ShutdownListener):
    def __init__(
        self,
        simulation_config: SimulationConfig,
        simulation_state_repository: SimulationStateRepository,
    ):
        ShutdownManager().register_listener(self)
        self._simulation_state_repository: SimulationStateRepository = simulation_state_repository
        # TODO_AFTER_MERGE: search for a better abstraction
        try:
            get_client()
            self.client_states: ClientStates | ClientStatesDask = ClientStatesDask(simulation_config)
        except ValueError:
            self.client_states = ClientStates(simulation_config)
        self._is_finished = False
        self._is_interrupted = False
        self.message_buffer: ClientMessageBuffer = ClientMessageBuffer()
        self.server_measurement = ServerTimeMeasurement()

    def wait_for_all_clients_starting_simulation(self) -> None:
        self.client_states.wait_for_all_clients_starting_simulation()

    def have_all_clients_started_simulation(self) -> bool:
        return self.client_states.have_all_clients_started_simulation()

    def have_all_clients_stopped_simulation(self) -> bool:
        return self.client_states.have_all_clients_stopped_simulation()

    def are_all_clients_connected_and_ready(self) -> bool:
        return self.client_states.are_all_clients_connected_and_ready()

    def is_running(self) -> bool:
        return not self._is_finished and not self._is_interrupted

    # callback of ShutdownManager => if this is called the server is interrupted
    def on_app_shutdown(self) -> None:
        self._is_interrupted = True
        if self._simulation_state_repository.current() != SimulationState.FINISHED:
            self.set_simulation_state(SimulationState.FAILED)

    def wait_for_all_clients_connected_and_ready(self) -> None:
        self.client_states.wait_for_all_clients_connected_and_ready()

    def set_is_finished(
        self,
        state: bool,
    ) -> None:
        self._is_finished = state
        self.set_simulation_state(SimulationState.FINISHED)

    def set_simulation_state(self, simulation_state: SimulationState) -> None:
        self._simulation_state_repository.update(simulation_state)

    def force_stop(self) -> None:
        self.on_app_shutdown()
        self._is_finished = True


# TODO_AFTER_MERGE: find common abstraction
class ServerStateDask(ShutdownListener):
    def __init__(
        self,
        simulation_config: SimulationConfig,
    ):
        ShutdownManager().register_listener(self)
        try:
            get_client()
            self.client_states: ClientStates | ClientStatesDask = ClientStatesDask(simulation_config)
        except ValueError:
            self.client_states = ClientStates(simulation_config)
        self._is_finished = False
        self._is_interrupted = False
        self.message_buffer: ClientMessageBuffer = ClientMessageBuffer()
        self.server_measurement = ServerTimeMeasurement()

    def wait_for_all_clients_starting_simulation(self) -> None:
        self.client_states.wait_for_all_clients_starting_simulation()

    def have_all_clients_started_simulation(self) -> bool:
        return self.client_states.have_all_clients_started_simulation()

    def have_all_clients_stopped_simulation(self) -> bool:
        return self.client_states.have_all_clients_stopped_simulation()

    def are_all_clients_connected_and_ready(self) -> bool:
        return self.client_states.are_all_clients_connected_and_ready()

    def is_running(self) -> bool:
        return not self._is_finished and not self._is_interrupted

    # callback of ShutdownManager => if this is called the server is interrupted
    def on_app_shutdown(self) -> None:
        self._is_interrupted = True

    def wait_for_all_clients_connected_and_ready(self) -> None:
        self.client_states.wait_for_all_clients_connected_and_ready()

    def set_is_finished(
        self,
        state: bool,
    ) -> None:
        self._is_finished = state

    def force_stop(self) -> None:
        self.on_app_shutdown()
        self._is_finished = True
