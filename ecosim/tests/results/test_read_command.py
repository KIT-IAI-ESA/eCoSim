from pathlib import Path

from ecosim.results.read_command import read_command_of_run
from ecosim.run_folder import RunFolder
from ecosim.simulation_folder import SimulationFolder
from ecosim_common.config.database_type import DatabaseType
from ecosim_server.config.server_config import DatabaseConfig


def create_simulation_folder(path: Path, simulation_config_name: str = "simulation.json") -> SimulationFolder:
    simulation = SimulationFolder(
        path=path,
        simulation_config=path / "server" / simulation_config_name,
        server_config=path / "server" / "preferences.ini",
        simulator_dir=path / "Modules",
    )
    simulation.simulation_config.parent.mkdir(parents=True)
    simulation.simulation_config.touch()
    return simulation


def create_finished_run_in(folder: Path) -> RunFolder:
    folder.mkdir(parents=True)
    (folder / "simulation_state.jsonl").touch()
    return RunFolder(path=folder)


def test_the_newest_run_of_a_simulation_is_read_through_the_simulation(tmp_path: Path) -> None:
    simulation = create_simulation_folder(path=tmp_path / "building")
    create_finished_run_in(folder=simulation.results / "2026-11-15_08-00-00")
    newest = create_finished_run_in(folder=simulation.results / "2026-11-16_09-30-12")

    read_command = read_command_of_run(
        simulation=simulation,
        run_folder=newest,
        database=DatabaseConfig.for_files(directory=newest.path),
        server_options=[],
    )

    assert read_command == ["ecosim", "results", str(simulation.path)]


def test_a_simulation_with_its_simulation_config_elsewhere_is_read_through_the_run_folder(tmp_path: Path) -> None:
    # ecosim results reads a folder as a simulation only when it has server/simulation.json
    simulation = create_simulation_folder(path=tmp_path / "building", simulation_config_name="variant.json")
    newest = create_finished_run_in(folder=simulation.results / "2026-11-16_09-30-12")

    read_command = read_command_of_run(
        simulation=simulation,
        run_folder=newest,
        database=DatabaseConfig.for_files(directory=newest.path),
        server_options=[],
    )

    assert read_command == ["ecosim", "results", str(newest.path)]


def test_a_run_in_a_folder_outside_the_simulation_is_read_through_its_folder(tmp_path: Path) -> None:
    simulation = create_simulation_folder(path=tmp_path / "building")
    run_folder = create_finished_run_in(folder=tmp_path / "my-first-try")

    read_command = read_command_of_run(
        simulation=simulation,
        run_folder=run_folder,
        database=DatabaseConfig.for_files(directory=run_folder.path),
        server_options=[],
    )

    assert read_command == ["ecosim", "results", str(run_folder.path)]


def test_a_postgres_run_is_read_as_postgres_with_its_database_options_but_without_the_password(tmp_path: Path) -> None:
    simulation = create_simulation_folder(path=tmp_path / "building")
    run_folder = RunFolder(path=simulation.results / "2026-11-16_09-30-12")
    # the command comes from the options of the run, so the password of the config does not matter
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

    read_command = read_command_of_run(simulation=simulation, run_folder=run_folder, database=database, server_options=server_options)

    assert read_command == [
        *("ecosim", "results", "--server-config", str(simulation.server_config), "--simulation-config", str(run_folder.simulation_config_copy)),
        *("--database-type", "postgres", "--database-port", "5433", "--database-schema", "run_2", "--database-ssl", "false"),
    ]
