from __future__ import annotations

import datetime
import os
import pickle
import shutil
from pathlib import Path

import distributed
from ecosim_common.communication.communication_protocol import CommunicationProtocol
from ecosim_common.communication.data.protocol_interface_value import ProtocolInterfaceValue
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.data.repositories_file_based import RepositoriesFileBased
from ecosim_server.measurement.measurement_entry import MeasurementEntry
from ecosim_server.measurement.measurement_repository_file import MeasurementRepositoryFile
from ecosim_server.simulation.state.simulation_state_repository_file import SimulationStateRepositoryFile
from ecosim_server.tech.db.server_time_measurement_repository_file import ServerTimeMeasurementRepositoryFile
from ecosim_test_common.resources.config_files import config_file_path
from tests.data.generate_server_config import generate_server_config
from tests.data.generate_simulation_config import HOUSE, WEATHER, generate_simulation_config_from_file

TIMESTAMP = datetime.datetime(2026, 8, 26, 10, 0, 0, tzinfo=datetime.timezone.utc)


def generate_file_based_repositories(
    directory: Path,
    communication_protocol: CommunicationProtocol = CommunicationProtocol.TCP_SOCKET,
    simulation_json: Path = config_file_path("simulation.json"),
) -> RepositoriesFileBased:
    return RepositoriesFileBased.create(
        server_config=generate_server_config(
            communication_protocol=communication_protocol,
            database_type=DatabaseType.FILE,
            database_directory=directory,
        ),
        simulation_config=generate_simulation_config_from_file(simulation_json=simulation_json),
    )


def create_values(temperature: float = 293.15) -> tuple[ProtocolInterfaceValue, ...]:
    return (ProtocolInterfaceValue(name="T_room", value=temperature),)


def test_the_repositories_are_the_file_based_ones(tmp_path: Path) -> None:
    repositories = generate_file_based_repositories(tmp_path)

    assert isinstance(repositories.simulation_state_repository, SimulationStateRepositoryFile)
    assert isinstance(repositories.server_time_measurement_repository, ServerTimeMeasurementRepositoryFile)
    assert isinstance(repositories.measurement_repository(HOUSE), MeasurementRepositoryFile)


def test_all_files_are_written_into_the_configured_directory(tmp_path: Path) -> None:
    repositories = generate_file_based_repositories(tmp_path)

    assert repositories.simulation_state_repository.file_path().parent == tmp_path
    assert repositories.server_time_measurement_repository.file_path().parent == tmp_path
    assert repositories.measurement_repository(HOUSE).file_path().parent == tmp_path


def test_every_client_gets_its_own_measurement_repository(tmp_path: Path) -> None:
    repositories = generate_file_based_repositories(tmp_path)

    assert repositories.measurement_repository(HOUSE) is not repositories.measurement_repository(WEATHER)


def test_the_measurement_repository_of_a_client_is_created_only_once(tmp_path: Path) -> None:
    repositories = generate_file_based_repositories(tmp_path)

    assert repositories.measurement_repository(HOUSE) is repositories.measurement_repository(HOUSE)


def test_the_measurement_file_is_named_after_the_simulator(tmp_path: Path) -> None:
    repositories = generate_file_based_repositories(tmp_path)

    assert repositories.measurement_repository(HOUSE).file_path().name == "module_house.jsonl"


def test_the_simulation_config_of_the_run_is_copied_into_the_directory(tmp_path: Path) -> None:
    generate_file_based_repositories(tmp_path)

    assert (tmp_path / "simulation.json").read_bytes() == config_file_path("simulation.json").read_bytes()


def test_results_written_next_to_the_simulation_config_leave_it_unchanged(tmp_path: Path) -> None:
    simulation_json = tmp_path / "simulation.json"
    shutil.copyfile(src=config_file_path("simulation.json"), dst=simulation_json)
    # long ago, because a write right after the copy can keep the same time
    os.utime(path=simulation_json, ns=(0, 0))

    generate_file_based_repositories(tmp_path, simulation_json=simulation_json)

    assert simulation_json.stat().st_mtime_ns == 0


def test_a_simulation_json_next_to_the_config_of_the_run_is_not_replaced(tmp_path: Path) -> None:
    shutil.copyfile(src=config_file_path("simulation.json"), dst=tmp_path / "simulation.json")
    simulation_bergwald_json = tmp_path / "simulation_bergwald.json"
    shutil.copyfile(src=config_file_path("simulation_bergwald.json"), dst=simulation_bergwald_json)

    generate_file_based_repositories(tmp_path, simulation_json=simulation_bergwald_json)

    assert (tmp_path / "simulation.json").read_bytes() == config_file_path("simulation.json").read_bytes()


def test_the_repositories_survive_a_pickle_round_trip(
    tmp_path: Path,
    dask_client: distributed.Client,
) -> None:
    repositories = generate_file_based_repositories(tmp_path, communication_protocol=CommunicationProtocol.DASK)
    repositories.measurement_repository(HOUSE).add(values=create_values(), timestamp=TIMESTAMP)

    restored = pickle.loads(pickle.dumps(repositories))

    assert restored.measurement_repository(HOUSE).all() == [MeasurementEntry(values=create_values(), timestamp=TIMESTAMP)]
