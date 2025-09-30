from __future__ import annotations

import threading
from typing import Any

from sqlalchemy import Column, Integer, Text

from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_types import DTO
from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base
from ecosim_server.simulation.state.simulation_state import SimulationState
from ecosim_server.simulation.state.simulation_state_repository import SimulationStateRepository


class SimulationStateRepositoryDB(SimulationStateRepository):
    _thread_lock = threading.Lock()

    def __init__(self, db_connection: DBConnection):
        self._db_connection = db_connection
        state = SimulationStateDTO(
            variation_id=0,
            state=SimulationState.NOT_READY.value,
        )
        self._state_id = self._db_connection.insert_into(state)

    def update(self,
               state: SimulationState,
               ):
        with self._thread_lock:
            self._db_connection.update(SimulationStateDTO(
                state_id=self._state_id,
                variation_id=0,
                state=state.db_entry,
            ))

    def current(self) -> SimulationState:
        return SimulationState.of_db_entry(self._db_connection.select_by_id(SimulationStateDTO, self._state_id).state)


class SimulationStateDTO(SimControlDB_Base, DTO[int]):
    __tablename__ = 'simulation_state'

    state_id = Column(Integer, primary_key=True, autoincrement=True)
    variation_id = Column(Integer)
    state = Column(Text)

    def id(self) -> int:
        return self.state_id  # type: ignore # during runtime this will be the ID (and not the column object)

    @staticmethod
    def id_column() -> Any:
        return SimulationStateDTO.state_id
