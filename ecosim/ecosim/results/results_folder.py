"""The folder of result files that FOLDER of ecosim results names."""

from pathlib import Path
from typing import Sequence

from ecosim_common.config.database_type import DatabaseType

from ecosim.report_lines import command_text, ecosim_program, shown_path
from ecosim.run_folder import RunFolder
from ecosim.simulation_folder import SIMULATION_CONFIG, hint_to_a_simulation


def results_folder_of(folder: Path) -> Path:
    """The folder itself, the newest run folder in it, or the newest run of a simulation."""
    if _holds_results(folder=folder):
        return folder
    if is_a_simulation(folder=folder):
        run_command = command_text(arguments=[*ecosim_program(), "run", str(folder)])
        no_results = f"{_shown_folder(folder=folder)} has no results yet. Run it with: {run_command}"
        return _newest_results_in(folder=folder / "results", no_results=no_results)
    return _newest_results_in(folder=folder, no_results=_no_results_message(folder=folder))


def is_a_simulation(folder: Path) -> bool:
    """ecosim results reads a folder with server/simulation.json as a simulation, and shows its newest run."""
    return (folder / SIMULATION_CONFIG).is_file()


def postgres_read_command(server_config: str, run_folder: RunFolder, database_options: Sequence[str] = ()) -> list[str]:
    # PostgreSQL has the names in lower case, the copy of simulation.json gives them as written there
    simulation_config = shown_path(path=run_folder.simulation_config_copy)
    # the --database-type of the run can differ from the type in the server config
    database_type = ["--database-type", DatabaseType.POSTGRES.serialized]
    read_options = ["--server-config", server_config, "--simulation-config", simulation_config, *database_type, *database_options]
    return [*ecosim_program(), "results", *read_options]


def _newest_results_in(folder: Path, no_results: str) -> Path:
    # the newest run comes before result files that a server started by hand wrote straight into the folder
    run_folder = RunFolder.newest(results=folder)
    if run_folder is None and _holds_results(folder=folder):
        return folder
    run_folder = run_folder or RunFolder(path=folder)
    if _holds_results(folder=run_folder.path):
        return run_folder.path
    if run_folder.holds_a_run() and run_folder.logs.is_dir():
        raise ValueError(_postgres_run_message(run_folder=run_folder))
    raise FileNotFoundError(no_results)


def _holds_results(folder: Path) -> bool:
    return (folder / "simulation_state.jsonl").is_file() or any(folder.glob("module_*.jsonl"))


def _postgres_run_message(run_folder: RunFolder) -> str:
    """A run folder with a copy of simulation.json but no states is from a run with its results in PostgreSQL."""
    simulation = run_folder.path.resolve().parent.parent
    server_config = shown_path(path=simulation / "server" / "preferences.ini") if is_a_simulation(folder=simulation) else "FILE"
    read_command = command_text(arguments=postgres_read_command(server_config=server_config, run_folder=run_folder))
    return (
        f"{_shown_folder(folder=run_folder.path)} holds no result files. A run with --database-type postgres stores them in PostgreSQL. "
        + f"To read them, add the --database options that the run had after -- to this command: {read_command}"
    )


def _no_results_message(folder: Path) -> str:
    message = f"There are no result files in {_shown_folder(folder=folder)}. "
    message += "Give a simulation folder, a run folder, or the folder the server wrote the result files to."
    # the old quick start wrote the results into results/ of building/Executable
    if not _holds_results(folder=folder / "results"):
        return message + hint_to_a_simulation(folder=folder, command_name="results")
    read_command = command_text(arguments=[*ecosim_program(), "results", str(folder / "results")])
    return f"{message} The folder results in it holds result files, so run: {read_command}"


def _shown_folder(folder: Path) -> str:
    shown = shown_path(path=folder)
    # '.' says nothing in a message, its name does
    return folder.resolve().name if shown == "." else shown
