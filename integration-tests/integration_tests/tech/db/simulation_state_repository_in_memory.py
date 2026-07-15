from dataclasses import dataclass, field
from typing import List

from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository


@dataclass(frozen=True)
class SimulationStateRepositoryInMemory(SimulationStateRepository):
    _states: List[SimulationState] = field(default_factory=list)

    def update(
        self,
        state: SimulationState,
    ) -> None:
        self._states.append(state)

    def current(self) -> SimulationState:
        if len(self._states) == 0:
            return SimulationState.NOT_READY
        return self._states[-1]
