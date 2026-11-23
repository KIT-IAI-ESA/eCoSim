import os
from pathlib import Path

import pytest
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim.results.results_command import main
from ecosim.run.run_command import main as run_main
from ecosim_common.tech.one_line_errors import DEBUG_HINT
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_test_common.test_data.building_simulation import skip_unless_fmpy_loads_the_building_fmus, write_building_simulation
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_output, create_simulator

from tests.command_errors import error_of
from tests.results.stored_results import write_results


def shown_lines(passed_arguments: list[str], capsys: pytest.CaptureFixture[str]) -> list[str]:
    main(passed_arguments=passed_arguments)
    return capsys.readouterr().out.splitlines()


def create_simulation(directory: Path) -> Path:
    (directory / "server").mkdir(parents=True)
    config_file(directory / "server", create_simulator("house", create_output("T_room")))
    return directory


def test_a_simulation_shows_its_newest_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(directory=tmp_path / "building")
    write_results(directory=simulation / "results" / "2026-11-15_08-00-00", steps=2)
    newest = write_results(directory=simulation / "results" / "2026-11-16_09-30-12", steps=3)

    lines = shown_lines(passed_arguments=[str(simulation)], capsys=capsys)

    assert lines[0] == f"Results:     {newest}"


def test_the_newest_run_comes_before_result_files_in_the_results_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(directory=tmp_path / "building")
    # as a server started manually with --database-directory building/results writes them
    write_results(directory=simulation / "results", steps=5)
    newest = write_results(directory=simulation / "results" / "2026-11-16_09-30-12", steps=3)

    lines = shown_lines(passed_arguments=[str(simulation)], capsys=capsys)

    assert lines[0] == f"Results:     {newest}"


def test_a_server_config_for_result_files_shows_the_files_in_its_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(directory=tmp_path / "results", steps=2)
    server_config = tmp_path / "preferences.ini"
    server_config.write_text(f"[server]\nport=1234\n[database]\ntype=file\ndirectory={results}\n", encoding="utf-8")

    lines = shown_lines(passed_arguments=["--server-config", str(server_config)], capsys=capsys)

    assert lines[0] == f"Results:     {results}"


def test_the_overview_leaves_out_the_inputs_unless_they_are_asked_for(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(directory=tmp_path / "results", steps=2)

    without_inputs = shown_lines(passed_arguments=[str(results)], capsys=capsys)
    with_inputs = shown_lines(passed_arguments=[str(results), "--inputs"], capsys=capsys)

    assert without_inputs[4].endswith("5 outputs, 1 input is left out (add --inputs)")
    assert with_inputs[4].endswith("5 outputs and 1 input")


def test_without_the_simulation_config_the_inputs_stay_in_the_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(directory=tmp_path / "results", steps=2)
    (results / "simulation.json").unlink()

    lines = shown_lines(passed_arguments=[str(results)], capsys=capsys)

    assert lines[4] == "Columns:     6 columns, inputs and outputs together"
    shown_columns = [line.split()[0] for line in lines if line.startswith(("house.", "weather."))]
    assert shown_columns == ["house.T_room", "house.T_out_in", "weather.T_out", *(f"weather.profile[{position}]" for position in range(3))]


def test_the_csv_has_a_time_column_and_the_chosen_columns_in_their_order(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(directory=tmp_path / "results", steps=2)
    csv_file = tmp_path / "temperatures.csv"

    passed_arguments = [str(results), "--interface", "house.T_room", "--interface", "weather", "--csv", str(csv_file)]

    lines = shown_lines(passed_arguments=passed_arguments, capsys=capsys)

    assert csv_file.read_text(encoding="utf-8").splitlines() == [
        "time,house.T_room,weather.T_out,weather.profile[0],weather.profile[1],weather.profile[2]",
        "2023-01-01T00:15:00+00:00,290.0,270.0,1.0,2.0,3.0",
        "2023-01-01T00:30:00+00:00,290.3333333333333,271.0,1.0,2.0,4.0",
    ]
    assert lines[-1] == f"Wrote 2 rows and 5 columns to {csv_file}."


def test_a_misspelled_interface_suggests_the_closest_column(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(directory=tmp_path / "results", steps=2)

    exit_code, error_line = error_of(arguments=["results", str(results), "--interface", "house.T_rom"], capsys=capsys)

    assert exit_code == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert "Did you mean house.T_room?" in error_line


def test_an_input_without_the_inputs_option_says_to_add_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(directory=tmp_path / "results", steps=2)

    _, error_line = error_of(arguments=["results", str(results), "--interface", "house.T_out_in"], capsys=capsys)

    assert error_line == f"ecosim results: error: house.T_out_in is an input. Add --inputs to show inputs. {DEBUG_HINT}"


def test_a_directory_and_the_server_config_together_are_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(directory=tmp_path / "results", steps=2)

    exit_code, error_line = error_of(arguments=["results", str(results), "--server-config", "preferences.ini"], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line == "ecosim results: error: pass either FOLDER or --server-config, not both"


def test_database_options_without_the_server_config_are_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, error_line = error_of(arguments=["results", "--database-schema", "run_2"], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line == "ecosim results: error: the --database options need --server-config"


def test_a_directory_with_the_database_type_file_shows_the_files_in_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(directory=tmp_path / "results", steps=2)

    lines = shown_lines(passed_arguments=[str(results), "--database-type", "file"], capsys=capsys)

    assert lines[0] == f"Results:     {results}"


def test_a_directory_that_does_not_exist_suggests_the_closest_directory(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "building").mkdir()

    exit_code, error_line = error_of(arguments=["results", str(tmp_path / "buildng")], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line.endswith("Did you mean building?")


def test_a_simulation_without_a_run_says_how_to_start_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(directory=tmp_path / "building")

    _, error_line = error_of(arguments=["results", str(simulation)], capsys=capsys)

    assert error_line.startswith(f"ecosim results: error: {simulation} has no results yet. Run it with: ")
    assert error_line.endswith(f"ecosim run {simulation} {DEBUG_HINT}")


def test_a_directory_with_results_in_its_results_folder_says_how_to_read_them(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    executable = tmp_path / "Executable"
    write_results(directory=executable / "results", steps=2)

    _, error_line = error_of(arguments=["results", str(executable)], capsys=capsys)

    assert "The folder results in it has result files. Read them with: " in error_line
    assert error_line.endswith(f"ecosim results {executable / 'results'} {DEBUG_HINT}")


def test_a_directory_inside_a_simulation_points_to_the_simulation_above_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(directory=tmp_path / "building")
    executable = simulation / "Executable"
    executable.mkdir()

    exit_code, error_line = error_of(arguments=["results", str(executable)], capsys=capsys)

    assert exit_code == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert error_line.startswith(
        f"ecosim results: error: There are no result files in {executable}. "
        + "Pass a simulation folder, a run folder or a folder with result files. The simulation is the folder above it. Run '",
    )
    assert error_line.endswith(f"ecosim results {os.path.relpath(simulation)}'. {DEBUG_HINT}")


def test_a_file_instead_of_a_directory_is_a_usage_error_with_its_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state_file = write_results(directory=tmp_path / "results", steps=2) / "simulation_state.jsonl"

    exit_code, error_line = error_of(arguments=["results", str(state_file)], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line == f"ecosim results: error: {state_file} is a file. Pass its folder {state_file.parent}."


def test_a_server_config_whose_directory_of_result_files_is_missing_says_so(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "simulation_results"
    server_config = tmp_path / "preferences.ini"
    server_config.write_text(f"[server]\nport=1234\n[database]\ntype=file\ndirectory={missing}\n", encoding="utf-8")

    _, error_line = error_of(arguments=["results", "--server-config", str(server_config)], capsys=capsys)

    assert error_line == (
        f"ecosim results: error: {missing} does not exist. A server with {server_config} writes its result files there. "
        + f"Pass the folder they are in instead. {DEBUG_HINT}"
    )


def test_options_after_a_double_dash_say_to_leave_it_out(capsys: pytest.CaptureFixture[str]) -> None:
    arguments = ["results", "--server-config", "preferences.ini", "--", "--database-schema", "run_2"]

    exit_code, error_line = error_of(arguments=arguments, capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line == "ecosim results: error: leave out the -- before the --database options. ecosim results takes them itself"


def test_the_run_directory_of_a_postgres_run_says_how_to_read_postgres(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(directory=tmp_path / "building")
    run_directory = simulation / "results" / "2026-11-16_09-30-12"
    (run_directory / "logs").mkdir(parents=True)
    (run_directory / "simulation.json").write_text((simulation / "server" / "simulation.json").read_text(encoding="utf-8"), encoding="utf-8")

    _, error_line = error_of(arguments=["results", str(simulation)], capsys=capsys)

    assert error_line.startswith(
        f"ecosim results: error: {run_directory} has no result files. A run with --database-type postgres stores them in PostgreSQL. "
        + "To read them, add the --database options of the run to this command: ",
    )
    assert error_line.endswith(
        f"ecosim results --server-config {simulation / 'server' / 'preferences.ini'} --simulation-config {run_directory / 'simulation.json'} "
        + f"--database-type postgres {DEBUG_HINT}",
    )


@pytest.mark.parametrize(
    "type_in_the_server_config, type_option",
    [("", []), ("type=file\n", ["--database-type", "postgres"])],
    ids=["postgres in the server config", "postgres by option"],
)
def test_a_rejected_postgres_connection_ends_in_one_line_with_the_address(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    type_in_the_server_config: str,
    type_option: list[str],
) -> None:
    server_config = tmp_path / "preferences.ini"
    database_section = f"[database]\n{type_in_the_server_config}server=\nport=5432\nusername=\nssl=false\n"
    server_config.write_text(f"[server]\nport=1234\n{database_section}", encoding="utf-8")
    port = get_free_port()
    arguments = ["results", "--server-config", str(server_config), *type_option, "--database-host", "127.0.0.1", "--database-port", str(port)]

    exit_code, error_line = error_of(arguments=arguments, capsys=capsys)

    assert exit_code == ShutdownManager.FAILED_RUN_EXIT_CODE
    assert f"127.0.0.1:{port}" in error_line


@skip_unless_fmpy_loads_the_building_fmus()
def test_a_finished_run_shows_the_command_that_reads_its_results(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = write_building_simulation(directory=tmp_path / "building")
    run_main(passed_arguments=[str(simulation), "--steps", "3"])
    read_command = capsys.readouterr().out.splitlines()[-1].removeprefix("Read them with: ")

    assert read_command.endswith(f"ecosim results {simulation}")
    passed_arguments = read_command.split("ecosim results ")[1].split()
    assert shown_lines(passed_arguments=passed_arguments, capsys=capsys)[1] == "Run:         finished, 3 steps of 15 min"
