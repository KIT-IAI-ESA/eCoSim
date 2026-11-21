from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from ecosim_server.config.server_config import ServerConfig
from ecosim_server.config.simulation_config import SimulationConfig
from ecosim_server.data.repositories_db import RepositoriesDB
from ecosim_server.results import read_database_results, read_file_results
from ecosim_server.simulation.state.simulation_state import SimulationState
from tests.results.stored_run import StoredRun
from psycopg import sql
from tests.tech.db.postgres_test_cluster import PostgresTestCluster


def write_database(stored_run: StoredRun, server_config: ServerConfig, steps: int) -> None:
    simulation_config = SimulationConfig.of_config_file_and_params(simulation_config_file=stored_run.simulation_config_file, steps=steps)
    repositories = RepositoriesDB.create(server_config=server_config, simulation_config=simulation_config)
    for client_id in simulation_config.client_ids():
        repository = repositories.measurement_repository(client_id=client_id)
        stored_run.write_steps(repository=repository, simulator_name=client_id.simulator_name, steps=steps)
    repositories.simulation_state_repository.update(SimulationState.FAILED)
    # the newest state is the state of the run; without clients, because a process can define a measurement table only once
    restored = RepositoriesDB.create(server_config=server_config, simulation_config=replace(simulation_config, restore=True, clients=[]))
    restored.simulation_state_repository.update(SimulationState.FINISHED)


def test_the_database_gives_the_same_table_as_the_files(plain_cluster: PostgresTestCluster, tmp_path: Path) -> None:
    stored_run = StoredRun.in_directory(directory=tmp_path, weather="weather_same_table", house="house_same_table")
    server_config = plain_cluster.server_config(database_name=f"test_{uuid4().hex}")
    stored_run.write_files(directory=tmp_path, steps=3)
    write_database(stored_run=stored_run, server_config=server_config, steps=3)

    from_database = read_database_results(database=server_config.database, simulation_config=stored_run.simulation_config_file, include_inputs=True)

    assert from_database == read_file_results(directory=tmp_path, include_inputs=True)


def test_the_times_come_in_utc_whatever_time_zone_the_database_has(plain_cluster: PostgresTestCluster, tmp_path: Path) -> None:
    stored_run = StoredRun.in_directory(directory=tmp_path, weather="weather_utc", house="house_utc")
    database_name = f"test_{uuid4().hex}"
    server_config = plain_cluster.server_config(database_name=database_name)
    write_database(stored_run=stored_run, server_config=server_config, steps=1)
    plain_cluster.execute(sql.SQL("ALTER DATABASE {} SET timezone TO 'Europe/Berlin'").format(sql.Identifier(database_name)))

    table = read_database_results(database=server_config.database, simulation_config=stored_run.simulation_config_file)

    assert [time.isoformat() for time in table.simulation_times] == [StoredRun.time_of(step=0).isoformat()]


def test_without_simulation_json_the_names_are_in_lower_case_and_the_inputs_still_known(
    plain_cluster: PostgresTestCluster,
    tmp_path: Path,
) -> None:
    stored_run = StoredRun.in_directory(directory=tmp_path, weather="Weather_Lower", house="House_Lower")
    server_config = plain_cluster.server_config(database_name=f"test_{uuid4().hex}")
    write_database(stored_run=stored_run, server_config=server_config, steps=1)

    table = read_database_results(database=server_config.database)

    assert table.column_names() == ("house_lower.t_room", "weather_lower.t_out", *(f"weather_lower.profile[{position}]" for position in range(3)))


def test_a_simulator_only_in_the_simulation_config_or_only_in_the_schema_gives_a_warning(
    plain_cluster: PostgresTestCluster,
    tmp_path: Path,
) -> None:
    stored_run = StoredRun.in_directory(directory=tmp_path, weather="weather_listed", house="house_unlisted")
    server_config = plain_cluster.server_config(database_name=f"test_{uuid4().hex}")
    write_database(stored_run=stored_run, server_config=server_config, steps=1)
    other_directory = tmp_path / "other"
    other_directory.mkdir()
    other_config_file = StoredRun.in_directory(directory=other_directory, weather="weather_listed", house="house_gone").simulation_config_file

    table = read_database_results(database=server_config.database, simulation_config=other_config_file)

    schema = server_config.database.schema
    assert table.warnings == (
        f"The schema {schema} has no results of the simulator house_gone in {other_config_file}.",
        f"{other_config_file} does not list house_unlisted. Its results in {schema}.module_house_unlisted are left out.",
    )


def test_an_empty_table_that_the_simulation_config_does_not_list_gives_no_warning(plain_cluster: PostgresTestCluster, tmp_path: Path) -> None:
    stored_run = StoredRun.in_directory(directory=tmp_path, weather="weather_beside_empty", house="house_beside_empty")
    database_name = f"test_{uuid4().hex}"
    server_config = plain_cluster.server_config(database_name=database_name)
    write_database(stored_run=stored_run, server_config=server_config, steps=1)
    empty_table = sql.SQL("CREATE TABLE {}.module_empty (timestamp timestamptz PRIMARY KEY)").format(sql.Identifier(server_config.database.schema))
    plain_cluster.execute(empty_table, database=database_name)

    table = read_database_results(database=server_config.database, simulation_config=stored_run.simulation_config_file)

    assert table.warnings == ()


def test_a_listed_simulator_without_a_stored_step_gives_a_warning(plain_cluster: PostgresTestCluster, tmp_path: Path) -> None:
    stored_run = StoredRun.in_directory(directory=tmp_path, weather="weather_with_step", house="house_without_step")
    database_name = f"test_{uuid4().hex}"
    server_config = plain_cluster.server_config(database_name=database_name)
    write_database(stored_run=stored_run, server_config=server_config, steps=1)
    schema = server_config.database.schema
    plain_cluster.execute(statement=sql.SQL("DELETE FROM {}.module_house_without_step").format(sql.Identifier(schema)), database=database_name)

    table = read_database_results(database=server_config.database, simulation_config=stored_run.simulation_config_file)

    assert table.warnings == (f"The schema {schema} has no results of the simulator house_without_step in {stored_run.simulation_config_file}.",)


def test_a_run_without_a_stored_step_has_no_results(plain_cluster: PostgresTestCluster, tmp_path: Path) -> None:
    stored_run = StoredRun.in_directory(directory=tmp_path, weather="weather_no_step", house="house_no_step")
    server_config = plain_cluster.server_config(database_name=f"test_{uuid4().hex}")
    simulation_config = SimulationConfig.of_config_file_and_params(simulation_config_file=stored_run.simulation_config_file, steps=1)
    RepositoriesDB.create(server_config=server_config, simulation_config=simulation_config)

    with pytest.raises(RuntimeError, match="has no results"):
        read_database_results(database=server_config.database, simulation_config=stored_run.simulation_config_file)


def test_a_missing_schema_is_shown_in_the_error(plain_cluster: PostgresTestCluster, tmp_path: Path) -> None:
    stored_run = StoredRun.in_directory(directory=tmp_path, weather="weather_schema", house="house_schema")
    server_config = plain_cluster.server_config(database_name=f"test_{uuid4().hex}")
    write_database(stored_run=stored_run, server_config=server_config, steps=1)

    with pytest.raises(RuntimeError, match="has no schema other_schema"):
        read_database_results(database=replace(server_config.database, schema="other_schema"))
