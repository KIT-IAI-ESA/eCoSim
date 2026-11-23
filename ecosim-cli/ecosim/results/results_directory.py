from pathlib import Path
from typing import Sequence

from ecosim_common.config.database_type import DatabaseType

from ecosim.report_lines import command_text, ecosim_program, shown_path
from ecosim.run_directory import RunDirectory
from ecosim.simulation_directory import SIMULATION_CONFIG, SimulationDirectory, hint_to_a_simulation


def results_directory_of(directory: Path) -> Path:
    """Returns the folder itself, the newest run folder in it or the newest run of a simulation."""
    if _has_results(directory=directory):
        return directory
    if is_a_simulation(directory=directory):
        run_command = command_text(arguments=[*ecosim_program(), "run", str(directory)])
        no_results = f"{_shown_directory(directory=directory)} has no results yet. Run it with: {run_command}"
        return _newest_results_in(directory=SimulationDirectory.of_path(path=directory).results, no_results=no_results)
    return _newest_results_in(directory=directory, no_results=_no_results_message(directory=directory))


def is_a_simulation(directory: Path) -> bool:
    return (directory / SIMULATION_CONFIG).is_file()


def postgres_read_command(server_config: str, run_directory: RunDirectory, database_options: Sequence[str] = ()) -> list[str]:
    # PostgreSQL stores the names in lower case, simulation.json has them as written
    simulation_config = shown_path(path=run_directory.simulation_config_copy)
    # the --database-type of the run can differ from the type in the server config
    database_type = ["--database-type", DatabaseType.POSTGRES.serialized]
    read_options = ["--server-config", server_config, "--simulation-config", simulation_config, *database_type, *database_options]
    return [*ecosim_program(), "results", *read_options]


def _newest_results_in(directory: Path, no_results: str) -> Path:
    run_directory = RunDirectory.newest(results=directory)
    if run_directory is None and _has_results(directory=directory):
        return directory
    run_directory = run_directory or RunDirectory(path=directory)
    if _has_results(directory=run_directory.path):
        return run_directory.path
    if run_directory.has_a_run() and run_directory.logs.is_dir():
        raise ValueError(_postgres_run_message(run_directory=run_directory))
    raise FileNotFoundError(no_results)


def _has_results(directory: Path) -> bool:
    return RunDirectory(path=directory).simulation_state_file.is_file() or any(directory.glob("module_*.jsonl"))


def _postgres_run_message(run_directory: RunDirectory) -> str:
    simulation = run_directory.path.resolve().parent.parent
    server_config = shown_path(path=SimulationDirectory.of_path(path=simulation).server_config) if is_a_simulation(directory=simulation) else "FILE"
    read_command = command_text(arguments=postgres_read_command(server_config=server_config, run_directory=run_directory))
    return (
        f"{_shown_directory(directory=run_directory.path)} has no result files. A run with --database-type postgres stores them in PostgreSQL. "
        + f"To read them, add the --database options of the run to this command: {read_command}"
    )


def _no_results_message(directory: Path) -> str:
    message = f"There are no result files in {_shown_directory(directory=directory)}. "
    message += "Pass a simulation folder, a run folder or a folder with result files."
    if not _has_results(directory=directory / "results"):
        return message + hint_to_a_simulation(directory=directory, command_name="results")
    read_command = command_text(arguments=[*ecosim_program(), "results", str(directory / "results")])
    return f"{message} The folder results in it has result files. Read them with: {read_command}"


def _shown_directory(directory: Path) -> str:
    shown = shown_path(path=directory)
    return directory.resolve().name if shown == "." else shown
