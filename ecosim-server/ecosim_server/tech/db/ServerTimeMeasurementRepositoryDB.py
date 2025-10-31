from __future__ import annotations

from typing import Any

from sqlalchemy import Column, Enum, DateTime, Integer

from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.db_types import DTO
from ecosim_server.tech.db.sqlalchemy_base import SimControlDB_Base
from ecosim_common.tech.logger.logger import ESPLogger
from ecosim_server.data.server_statistics_repository import ServerTimeMeasurementRepository
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType


class ServerTimeMeasurementRepositoryDB(ServerTimeMeasurementRepository):
    _logger = ESPLogger("ServerStatisticsRepositoryDB")

    def __init__(
        self,
        db_connection: DBConnection,
    ):
        self._db_connection = db_connection

    def put(
        self,
        server_time_measurement: ServerTimeMeasurement,
    ):
        for measurement_type in ServerTimeMeasurementType:
            self._db_connection.upsert(ServerTimeMeasurementDBEntry.of(server_time_measurement.get(measurement_type)))


class ServerTimeMeasurementDBEntry(SimControlDB_Base, DTO[ServerTimeMeasurementType]):
    __tablename__ = 'server_time_measurement'

    time_measurement_type = Column(Enum(ServerTimeMeasurementType), primary_key=True)
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
