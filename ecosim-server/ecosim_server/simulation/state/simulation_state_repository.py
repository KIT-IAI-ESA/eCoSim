from abc import ABC, abstractmethod

from ecosim_server.simulation.state.simulation_state import SimulationState


class SimulationStateRepository(ABC):

    @abstractmethod
    def update(
        self,
        state: SimulationState,
    ) -> None:
        pass

    @abstractmethod
    def current(self) -> SimulationState:
        pass
