from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import override

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository
from ecosim_server.tech.db.file_repository import FileRepository


@dataclass
class SimulationStateEntry:
    """The state is wrapped, because only a dataclass can be stored by the FileRepository."""

    state: SimulationState


@dataclass(frozen=True)
class SimulationStateEntryFileRepository(FileRepository[SimulationStateEntry]):
    @override
    def entry_type(self) -> type[SimulationStateEntry]:
        return SimulationStateEntry


@dataclass(frozen=True)
class SimulationStateRepositoryFile(SimulationStateRepository):
    """Appends every state change to the file, so the last entry is the current state."""

    _states: SimulationStateEntryFileRepository = field()

    @staticmethod
    def create(
        directory: Path,
        communication_protocol: CommunicationProtocol,
    ) -> SimulationStateRepositoryFile:
        return SimulationStateRepositoryFile(
            _states=SimulationStateEntryFileRepository(
                _file_path=directory / "simulation_state.jsonl",
                _write_lock=ParallelLock.for_protocol(communication_protocol, dask_name="simulation_state.jsonl_lock"),
            ),
        )

    @override
    def update(
        self,
        state: SimulationState,
    ) -> None:
        self._states.add(SimulationStateEntry(state=state))

    @override
    def current(self) -> SimulationState:
        entries = self._states.all()
        if not entries:
            return SimulationState.NOT_READY
        return entries[-1].state

    def file_path(self) -> Path:
        return self._states.file_path()
