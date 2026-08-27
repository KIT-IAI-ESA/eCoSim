from __future__ import annotations

import pickle
from pathlib import Path

import distributed
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_server.measurement.server_time_measurement import ServerTimeMeasurement, ServerTimeMeasurementType
from ecosim_server.tech.db.server_time_measurement_repository_file import ServerTimeMeasurementRepositoryFile


def create_repository(
    directory: Path,
    communication_protocol: CommunicationProtocol,
) -> ServerTimeMeasurementRepositoryFile:
    return ServerTimeMeasurementRepositoryFile.create(
        directory=directory,
        communication_protocol=communication_protocol,
    )


def create_measurement(
    communication_protocol: CommunicationProtocol,
    *measured_types: ServerTimeMeasurementType,
) -> ServerTimeMeasurement:
    measurement = ServerTimeMeasurement(protocol=communication_protocol)
    for measured_type in measured_types:
        measurement.set_start(measured_type)
        measurement.set_end(measured_type)
    return measurement


def test_an_unknown_type_has_no_start_and_no_end_time(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(tmp_path, communication_protocol=communication_protocol)

    assert repository.get_start(ServerTimeMeasurementType.SERVER_UPTIME) is None
    assert repository.get_end(ServerTimeMeasurementType.SERVER_UPTIME) is None


def test_a_put_measurement_is_returned_by_get_start_and_get_end(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(tmp_path, communication_protocol=communication_protocol)
    measurement = create_measurement(communication_protocol, ServerTimeMeasurementType.SERVER_UPTIME)
    entry = measurement.get_or_none(ServerTimeMeasurementType.SERVER_UPTIME)

    repository.put(measurement)

    assert entry is not None
    assert repository.get_start(ServerTimeMeasurementType.SERVER_UPTIME) == entry.start_time
    assert repository.get_end(ServerTimeMeasurementType.SERVER_UPTIME) == entry.end_time


def test_a_phase_the_run_never_entered_is_not_persisted(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(tmp_path, communication_protocol=communication_protocol)

    repository.put(create_measurement(communication_protocol, ServerTimeMeasurementType.SERVER_UPTIME))

    assert repository.get_start(ServerTimeMeasurementType.SIMULATION_START) is None


def test_every_measured_type_is_persisted(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(tmp_path, communication_protocol=communication_protocol)

    repository.put(
        create_measurement(
            communication_protocol,
            ServerTimeMeasurementType.SIMULATION_START,
            ServerTimeMeasurementType.SERVER_UPTIME,
        ),
    )

    assert repository.get_start(ServerTimeMeasurementType.SIMULATION_START) is not None
    assert repository.get_start(ServerTimeMeasurementType.SERVER_UPTIME) is not None


def test_the_latest_entry_of_a_type_wins(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(tmp_path, communication_protocol=communication_protocol)
    latest_measurement = create_measurement(communication_protocol, ServerTimeMeasurementType.SERVER_UPTIME)
    latest_entry = latest_measurement.get_or_none(ServerTimeMeasurementType.SERVER_UPTIME)

    repository.put(create_measurement(communication_protocol, ServerTimeMeasurementType.SERVER_UPTIME))
    repository.put(latest_measurement)

    assert latest_entry is not None
    assert repository.get_end(ServerTimeMeasurementType.SERVER_UPTIME) == latest_entry.end_time


def test_the_measurements_are_persisted_for_a_new_repository_instance(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    measurement = create_measurement(communication_protocol, ServerTimeMeasurementType.SERVER_UPTIME)
    entry = measurement.get_or_none(ServerTimeMeasurementType.SERVER_UPTIME)
    create_repository(tmp_path, communication_protocol=communication_protocol).put(measurement)

    assert entry is not None
    assert (
        create_repository(tmp_path, communication_protocol=communication_protocol).get_start(
            ServerTimeMeasurementType.SERVER_UPTIME,
        )
        == entry.start_time
    )


def test_the_repository_survives_a_pickle_round_trip(
    tmp_path: Path,
    dask_client: distributed.Client,
) -> None:
    repository = create_repository(tmp_path, communication_protocol=CommunicationProtocol.DASK)
    repository.put(create_measurement(CommunicationProtocol.DASK, ServerTimeMeasurementType.SERVER_UPTIME))

    restored = pickle.loads(pickle.dumps(repository))

    assert restored.get_start(ServerTimeMeasurementType.SERVER_UPTIME) is not None
