from __future__ import annotations

from datetime import datetime
from typing import Any, override

from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_types import DTO
from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base
from sqlalchemy import Column, DateTime, Enum, Integer


class ServerTimeMeasurementRepositoryDB(ServerTimeMeasurementRepository):
    def __init__(
        self,
        db_connection: DBConnection,
    ):
        self._db_connection = db_connection

    @override
    def put(
        self,
        server_time_measurement: ServerTimeMeasurement,
    ) -> None:
        for measurement_type in ServerTimeMeasurementType:
            entry = server_time_measurement.get_or_none(measurement_type)
            if entry is None:  # a phase the run never entered doesn't have anything to persist
                continue
            self._db_connection.upsert(ServerTimeMeasurementDBEntry.of(entry))

    @override
    def get_start(
        self,
        type: ServerTimeMeasurementType,
    ) -> datetime | None:
        measurement: ServerTimeMeasurementDBEntry | None = self._db_connection.select_by_id(  # type: ignore[assignment]
            ServerTimeMeasurementDBEntry,
            type,
        )
        if measurement is None:
            self._logger.debug("DB: Measurement type %s not found", type)
            return None
        return measurement.start_time  # type: ignore

    @override
    def get_end(
        self,
        type: ServerTimeMeasurementType,
    ) -> datetime | None:
        measurement: ServerTimeMeasurementDBEntry | None = self._db_connection.select_by_id(  # type: ignore[assignment]
            ServerTimeMeasurementDBEntry,
            type,
        )
        if measurement is None:
            self._logger.debug("DB: Measurement type %s not found", type)
            return None
        return measurement.end_time  # type: ignore


class ServerTimeMeasurementDBEntry(SimControlDB_Base, DTO[ServerTimeMeasurementType]):
    __tablename__ = "server_time_measurement"

    time_measurement_type = Column(Enum(ServerTimeMeasurementType), primary_key=True)  # type: ignore
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    run_time_in_seconds = Column(Integer, nullable=False)

    def id(self) -> ServerTimeMeasurementType:
        return self.time_measurement_type  # type: ignore # during runtime this will be the actual type and not the column

    @staticmethod
    def id_column() -> Any:
        return ServerTimeMeasurementDBEntry.time_measurement_type

    @classmethod
    def of(
        cls,
        time_measurement: ServerTimeMeasurement.Entry,
    ) -> ServerTimeMeasurementDBEntry:
        return ServerTimeMeasurementDBEntry(
            time_measurement_type=time_measurement.type,
            start_time=time_measurement.start_time,
            end_time=time_measurement.end_time,
            run_time_in_seconds=time_measurement.run_time_in_seconds,
        )
