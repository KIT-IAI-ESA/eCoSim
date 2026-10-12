from __future__ import annotations

from typing import Any, List, cast

import pytest
from ecosim_common.config.client_id import ClientID
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.measurement.measurement_repository_db import MeasurementRepositoryDB
from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_test_common.resources.config_files import config_file_path
from sqlalchemy import JSON, Float


class _RecordingDBConnection:
    default_schema = "postgres"

    def __init__(self) -> None:
        self.created_tables: List[Any] = []

    def create_measurement_table(self, table: Any) -> None:
        self.created_tables.append(table)


def _create(
    db_connection: _RecordingDBConnection,
    simulator_name: str,
) -> MeasurementRepositoryDB:
    return MeasurementRepositoryDB.create(
        simulation_config=SimulationConfig.of_config_file_and_params(config_file_path("simulation.json"), 100),
        client_id=ClientID(model_name=simulator_name, simulator_name=simulator_name),
        db_connection=cast(DBConnection, db_connection),
    )


@pytest.fixture(scope="module")
def weather_table() -> Any:
    # created only once: SQLAlchemy refuses to define the same table twice
    db_connection = _RecordingDBConnection()
    _create(db_connection, simulator_name="weather")
    return db_connection.created_tables[0]


def test_an_unknown_client_cannot_get_a_repository() -> None:
    with pytest.raises(RuntimeError):
        _create(_RecordingDBConnection(), simulator_name="unknown")


def test_the_table_is_named_after_the_simulator(weather_table: Any) -> None:
    assert weather_table.__tablename__ == "module_weather"


def test_the_timestamp_is_the_primary_key(weather_table: Any) -> None:
    assert [column.name for column in weather_table.__table__.primary_key] == ["timestamp"]


def test_the_number_column_of_an_interface_is_a_float(weather_table: Any) -> None:
    assert isinstance(weather_table.__table__.columns["o_t_out"].type, Float)


def test_the_json_column_of_an_interface_is_json(weather_table: Any) -> None:
    assert isinstance(weather_table.__table__.columns["o_t_out_json"].type, JSON)
