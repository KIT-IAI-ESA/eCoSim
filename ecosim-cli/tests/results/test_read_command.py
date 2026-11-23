from pathlib import Path

from ecosim.results.read_command import read_command_of_run
from ecosim.run_directory import RunDirectory
from ecosim.simulation_directory import SimulationDirectory
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.server_config import DatabaseConfig


def create_simulation_directory(path: Path, simulation_config_name: str = "simulation.json") -> SimulationDirectory:
    simulation = SimulationDirectory(
        path=path,
        simulation_config=path / "server" / simulation_config_name,
        server_config=path / "server" / "preferences.ini",
        simulator_dir=path / "modules",
    )
    simulation.simulation_config.parent.mkdir(parents=True)
    simulation.simulation_config.touch()
    return simulation


def create_finished_run_in(directory: Path) -> RunDirectory:
    directory.mkdir(parents=True)
    (directory / "simulation_state.jsonl").touch()
    return RunDirectory(path=directory)


def test_the_newest_run_of_a_simulation_is_read_through_the_simulation(tmp_path: Path) -> None:
    simulation = create_simulation_directory(path=tmp_path / "building")
    create_finished_run_in(directory=simulation.results / "2026-11-15_08-00-00")
    newest = create_finished_run_in(directory=simulation.results / "2026-11-16_09-30-12")

    read_command = read_command_of_run(
        simulation=simulation,
        run_directory=newest,
        database=DatabaseConfig.for_files(directory=newest.path),
        server_options=[],
    )

    assert read_command[-2:] == ["results", str(simulation.path)]


def test_a_run_with_another_simulation_config_is_read_through_its_run_directory(tmp_path: Path) -> None:
    simulation = create_simulation_directory(path=tmp_path / "building", simulation_config_name="variant.json")
    newest = create_finished_run_in(directory=simulation.results / "2026-11-16_09-30-12")

    read_command = read_command_of_run(
        simulation=simulation,
        run_directory=newest,
        database=DatabaseConfig.for_files(directory=newest.path),
        server_options=[],
    )

    assert read_command[-2:] == ["results", str(newest.path)]


def test_a_run_in_a_directory_outside_the_simulation_is_read_through_its_directory(tmp_path: Path) -> None:
    simulation = create_simulation_directory(path=tmp_path / "building")
    run_directory = create_finished_run_in(directory=tmp_path / "my-first-try")

    read_command = read_command_of_run(
        simulation=simulation,
        run_directory=run_directory,
        database=DatabaseConfig.for_files(directory=run_directory.path),
        server_options=[],
    )

    assert read_command[-2:] == ["results", str(run_directory.path)]


def test_a_postgres_run_is_read_with_its_database_options_without_the_password(tmp_path: Path) -> None:
    simulation = create_simulation_directory(path=tmp_path / "building")
    run_directory = RunDirectory(path=simulation.results / "2026-11-16_09-30-12")
    database = DatabaseConfig(
        host="127.0.0.1",
        port=5433,
        ssl=False,
        drop_existing_schema=False,
        username="",
        password="",
        schema="run_2",
        type=DatabaseType.POSTGRES,
    )
    server_options = [
        "--database-schema",
        "run_2",
        "--database-user-password=secret",
        "--database-port",
        "5433",
        "--image-renderer-port",
        "5",
        "--database-ssl",
        "false",
    ]

    read_command = read_command_of_run(simulation=simulation, run_directory=run_directory, database=database, server_options=server_options)

    assert read_command[read_command.index("results") :] == [
        *("results", "--server-config", str(simulation.server_config), "--simulation-config", str(run_directory.simulation_config_copy)),
        *("--database-type", "postgres", "--database-port", "5433", "--database-schema", "run_2", "--database-ssl", "false"),
    ]
