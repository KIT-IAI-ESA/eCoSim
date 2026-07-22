from dataclasses import dataclass, field

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.structures.esp_list import ESPList, ThreadESPList
from ecosim_common.tech.structures.esp_structure_type import ESPStructureType
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository


@dataclass(frozen=True)
class SimulationStateRepositoryInMemory(SimulationStateRepository):
    _states: ESPList[SimulationState] = field(default_factory=lambda: ThreadESPList[SimulationState]())

    @staticmethod
    def for_communication_protocol(protocol: CommunicationProtocol) -> "SimulationStateRepositoryInMemory":
        return SimulationStateRepositoryInMemory(
            _states=ESPList.of_type(list_type=ESPStructureType.THREAD if protocol == CommunicationProtocol.TCP_SOCKET else ESPStructureType.DASK),
        )

    def update(
        self,
        state: SimulationState,
    ) -> None:
        self._states.append(state)

    def current(self) -> SimulationState:
        if len(self._states) == 0:
            return SimulationState.NOT_READY
        return self._states[-1]
