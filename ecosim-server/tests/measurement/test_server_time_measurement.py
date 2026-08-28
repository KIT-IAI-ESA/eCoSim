from __future__ import annotations

from typing import Any, List, cast

from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.tech.db.db_connection import DBConnection
from ecosim_server.tech.db.server_time_measurement_repository_db import ServerTimeMeasurementRepositoryDB


class _RecordingDBConnection:
    def __init__(self) -> None:
        self.upserted: List[Any] = []

    def upsert(self, entity: Any) -> None:
        self.upserted.append(entity)


def _measurement() -> ServerTimeMeasurement:
    return ServerTimeMeasurement(protocol=CommunicationProtocol.TCP_SOCKET)


def _measured(
    measurement: ServerTimeMeasurement,
    type: ServerTimeMeasurementType,
) -> None:
    measurement.set_start(type)
    measurement.set_end(type)


def _upserted_types(upserted: List[Any]) -> set[ServerTimeMeasurementType]:
    return {cast(ServerTimeMeasurementType, entry.time_measurement_type) for entry in upserted}


# --- the restore type is its own measurement ---


def test_the_restore_run_is_not_an_alias_of_the_server_uptime() -> None:
    assert ServerTimeMeasurementType.RESTORE_SIMULATION_RUN is not ServerTimeMeasurementType.SERVER_UPTIME


def test_the_restore_run_is_an_own_member_of_the_type() -> None:
    assert ServerTimeMeasurementType.RESTORE_SIMULATION_RUN in list(ServerTimeMeasurementType)


def test_measuring_the_restore_run_does_not_end_the_server_uptime() -> None:
    measurement = _measurement()
    measurement.set_start(ServerTimeMeasurementType.SERVER_UPTIME)

    _measured(measurement, ServerTimeMeasurementType.RESTORE_SIMULATION_RUN)
    measurement.set_end(ServerTimeMeasurementType.SERVER_UPTIME)

    server_uptime = measurement.get_or_none(ServerTimeMeasurementType.SERVER_UPTIME)
    restore = measurement.get_or_none(ServerTimeMeasurementType.RESTORE_SIMULATION_RUN)
    assert server_uptime is not None and restore is not None
    assert server_uptime.end_time >= restore.end_time, "the restore ended the server uptime measurement"


# --- reading a measurement that never ran ---


def test_get_or_none_returns_none_for_a_measurement_that_never_ran() -> None:
    assert _measurement().get_or_none(ServerTimeMeasurementType.SIMULATION_START) is None


def test_get_or_none_returns_none_when_only_the_start_was_set() -> None:
    measurement = _measurement()
    measurement.set_start(ServerTimeMeasurementType.SIMULATION_START)
    assert measurement.get_or_none(ServerTimeMeasurementType.SIMULATION_START) is None


def test_get_or_none_returns_the_entry_of_a_completed_measurement() -> None:
    measurement = _measurement()
    _measured(measurement, ServerTimeMeasurementType.SIMULATION_START)

    entry = measurement.get_or_none(ServerTimeMeasurementType.SIMULATION_START)

    assert entry is not None
    assert entry.type == ServerTimeMeasurementType.SIMULATION_START
    assert entry.end_time >= entry.start_time


# --- what a restore run persists ---


def test_put_skips_a_measurement_that_never_ran() -> None:
    """This is the restore run that used to raise 'KeyError: ServerTimeMeasurementType.SIMULATION_START'."""
    measurement = _measurement()
    db_connection = _RecordingDBConnection()
    for type in (
        ServerTimeMeasurementType.RESTORE_SIMULATION_RUN,
        ServerTimeMeasurementType.SIMULATION_EXECUTION,
        ServerTimeMeasurementType.SIMULATION_STOP,
        ServerTimeMeasurementType.SERVER_UPTIME,
    ):
        _measured(measurement, type)

    ServerTimeMeasurementRepositoryDB(db_connection=cast(DBConnection, db_connection)).put(measurement)

    assert ServerTimeMeasurementType.SIMULATION_START not in _upserted_types(db_connection.upserted)


def test_put_persists_the_restore_run_of_a_restored_simulation() -> None:
    measurement = _measurement()
    db_connection = _RecordingDBConnection()
    _measured(measurement, ServerTimeMeasurementType.RESTORE_SIMULATION_RUN)

    ServerTimeMeasurementRepositoryDB(db_connection=cast(DBConnection, db_connection)).put(measurement)

    assert _upserted_types(db_connection.upserted) == {ServerTimeMeasurementType.RESTORE_SIMULATION_RUN}


def test_put_persists_every_measurement_of_a_normal_run() -> None:
    measurement = _measurement()
    db_connection = _RecordingDBConnection()
    for type in (
        ServerTimeMeasurementType.SIMULATION_START,
        ServerTimeMeasurementType.SIMULATION_EXECUTION,
        ServerTimeMeasurementType.SIMULATION_STOP,
        ServerTimeMeasurementType.SERVER_UPTIME,
    ):
        _measured(measurement, type)

    ServerTimeMeasurementRepositoryDB(db_connection=cast(DBConnection, db_connection)).put(measurement)

    assert _upserted_types(db_connection.upserted) == {
        ServerTimeMeasurementType.SIMULATION_START,
        ServerTimeMeasurementType.SIMULATION_EXECUTION,
        ServerTimeMeasurementType.SIMULATION_STOP,
        ServerTimeMeasurementType.SERVER_UPTIME,
    }
