from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_common.tech.parallel.parallel_lock import ParallelLock
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository
from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_types import DTO
from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base
from sqlalchemy import Column, Integer, Text


# TODO_OSR: move to different package ('simdb' is not used anymore)
# TODO_OSR: remove variant stuff
@dataclass
class SimulationStateRepositoryDB(SimulationStateRepository):
    _db_connection: DBConnection = field()
    _write_lock: ParallelLock = field()
    _state_id: Any = field(default=None, init=False)
    _logger: ESPLogger = field(default_factory=lambda: ESPLogger("SimulationStateRepositoryDB"))

    def __post_init__(self) -> None:
        state = SimulationStateDTO(
            variation_id=0,  # TODO_OSR: remove
            state=SimulationState.NOT_READY.value,
        )
        self._state_id = self._db_connection.insert_into(state)

    def update(
        self,
        state: SimulationState,
    ) -> None:
        with self._write_lock:
            self._db_connection.update(
                SimulationStateDTO(
                    state_id=self._state_id,
                    variation_id=0,
                    state=state.db_entry,
                ),
            )

    def current(self) -> SimulationState:
        dto: SimulationStateDTO | None = self._db_connection.select_by_id(SimulationStateDTO, self._state_id)  # type: ignore
        if dto is None:
            SimulationStateRepositoryDB._logger.error("Could not find state in database for state_id %s.", self._state_id)
            return SimulationState.NOT_READY
        return SimulationState.of_db_entry(dto.state)  # type: ignore


class SimulationStateDTO(SimControlDB_Base, DTO[int]):
    __tablename__ = "simulation_state"

    state_id = Column(Integer, primary_key=True, autoincrement=True)
    variation_id = Column(Integer)
    state = Column(Text)

    def id(self) -> int:
        return self.state_id  # type: ignore # during runtime this will be the ID (and not the column object)

    @staticmethod
    def id_column() -> Any:
        return SimulationStateDTO.state_id
