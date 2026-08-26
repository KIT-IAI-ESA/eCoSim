from __future__ import annotations

import datetime
import pickle
from pathlib import Path
from typing import List, Tuple

import distributed
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository_file import MeasurementRepositoryFile
from ecosim_test_common.resources.config_files import config_file_path

TIMESTAMP = datetime.datetime(2026, 8, 26, 10, 0, 0, tzinfo=datetime.timezone.utc)


def simulation_config() -> SimulationConfig:
    return SimulationConfig.of_config_file_and_params(config_file_path("simulation.json"), 100)


def create_repository(
    directory: Path,
    communication_protocol: CommunicationProtocol,
    simulator_name: str = "house",
) -> MeasurementRepositoryFile:
    return MeasurementRepositoryFile.create(
        directory=directory,
        simulator_name=simulator_name,
        communication_protocol=communication_protocol,
    )


def create_values(temperature: float = 293.15) -> Tuple[ProtocolInterfaceValue, ...]:
    return (
        ProtocolInterfaceValue(name="T_room", value=temperature),
        ProtocolInterfaceValue(name="profile", value=[1.0, 2.0]),
    )


def test_the_file_is_named_after_the_simulator(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(
        tmp_path,
        communication_protocol=communication_protocol,
    )

    assert repository.file_path().name == "module_house.jsonl"


def test_every_simulator_gets_its_own_file(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    house = create_repository(
        tmp_path,
        simulator_name="house",
        communication_protocol=communication_protocol,
    )
    weather = create_repository(
        tmp_path,
        simulator_name="weather",
        communication_protocol=communication_protocol,
    )
    assert house.file_path() != weather.file_path()


def test_an_added_measurement_is_returned_by_all(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(
        tmp_path,
        communication_protocol,
    )

    repository.add(values=create_values(), timestamp=TIMESTAMP)

    assert repository.all() == [MeasurementEntry(values=create_values(), timestamp=TIMESTAMP)]


def test_the_measurements_are_returned_in_the_order_they_were_added(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    repository = create_repository(
        tmp_path,
        communication_protocol=communication_protocol,
    )
    timestamps: List[datetime.datetime] = [TIMESTAMP + datetime.timedelta(minutes=minute) for minute in range(3)]

    for minute, timestamp in enumerate(timestamps):
        repository.add(values=create_values(293.15 + minute), timestamp=timestamp)

    assert [entry.timestamp for entry in repository.all()] == timestamps


def test_all_is_empty_before_the_first_measurement(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    assert (
        create_repository(
            tmp_path,
            communication_protocol=communication_protocol,
        ).all()
        == []
    )


def test_the_measurements_are_persisted_for_a_new_repository_instance(
    tmp_path: Path,
    communication_protocol: CommunicationProtocol,
) -> None:
    create_repository(
        tmp_path,
        communication_protocol=communication_protocol,
    ).add(values=create_values(), timestamp=TIMESTAMP)

    assert create_repository(
        tmp_path,
        communication_protocol=communication_protocol,
    ).all() == [MeasurementEntry(values=create_values(), timestamp=TIMESTAMP)]


def test_the_repository_survives_a_pickle_round_trip(
    tmp_path: Path,
    dask_client: distributed.Client,
) -> None:
    repository = create_repository(
        tmp_path,
        simulator_name="DASK",
        communication_protocol=CommunicationProtocol.DASK,
    )

    repository.add(values=create_values(), timestamp=TIMESTAMP)

    restored = pickle.loads(pickle.dumps(repository))

    assert restored.all() == [MeasurementEntry(values=create_values(), timestamp=TIMESTAMP)]
