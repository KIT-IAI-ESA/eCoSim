import os
from pathlib import Path

import pytest
from ecosim.main import run_command
from ecosim.results.results_command import main
from ecosim.run.run_command import main as run_main
from ecosim_common.tech.port_utils import get_free_port
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.test_data.building_simulation import BUILDING_MODULES, write_building_simulation
from ecosim_test_common.test_data.generate_simulation_file import config_file, create_output, create_simulator

from tests.results.stored_results import write_results

ONE_LINE_HINT = " (run with --debug for the full traceback)"


def output_of(passed_arguments: list[str], capsys: pytest.CaptureFixture[str]) -> list[str]:
    assert main(passed_arguments=passed_arguments) == 0
    return capsys.readouterr().out.splitlines()


def error_of(passed_arguments: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int | str | None, str]:
    """The exit code and the last line on stderr, through the ecosim command."""
    with pytest.raises(SystemExit) as exit_info:
        run_command(arguments=["results", *passed_arguments])
    return exit_info.value.code, capsys.readouterr().err.splitlines()[-1]


def create_simulation(folder: Path) -> Path:
    (folder / "server").mkdir(parents=True)
    config_file(folder / "server", create_simulator("house", create_output("T_room")))
    return folder


def test_a_simulation_shows_its_newest_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(folder=tmp_path / "building")
    write_results(folder=simulation / "results" / "2026-11-15_08-00-00", steps=2)
    newest = write_results(folder=simulation / "results" / "2026-11-16_09-30-12", steps=3)

    lines = output_of(passed_arguments=[str(simulation)], capsys=capsys)

    assert lines[:2] == [f"Results:     {newest}", "Run:         finished, 3 steps of 15 min"]
    assert lines[-1] == "Add --csv results.csv to write the table to a file."


def test_the_newest_run_of_a_simulation_comes_before_result_files_straight_in_its_results_folder(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    simulation = create_simulation(folder=tmp_path / "building")
    # as a server started by hand with --database-directory building/results writes them
    write_results(folder=simulation / "results", steps=5)
    newest = write_results(folder=simulation / "results" / "2026-11-16_09-30-12", steps=3)

    lines = output_of(passed_arguments=[str(simulation)], capsys=capsys)

    assert lines[:2] == [f"Results:     {newest}", "Run:         finished, 3 steps of 15 min"]


def test_a_server_config_for_result_files_shows_the_files_in_its_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(folder=tmp_path / "results", steps=2)
    server_config = tmp_path / "preferences.ini"
    server_config.write_text(f"[server]\nport=1234\n[database]\ntype=file\ndirectory={results}\n", encoding="utf-8")

    lines = output_of(passed_arguments=["--server-config", str(server_config)], capsys=capsys)

    assert lines[:2] == [f"Results:     {results}", "Run:         finished, 2 steps of 15 min"]


def test_the_overview_leaves_out_the_inputs_unless_they_are_asked_for(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(folder=tmp_path / "results", steps=2)

    without_inputs = output_of(passed_arguments=[str(results)], capsys=capsys)
    with_inputs = output_of(passed_arguments=[str(results), "--inputs"], capsys=capsys)

    assert (without_inputs[4], with_inputs[4]) == ("Columns:     2 outputs, 1 input is left out (add --inputs)", "Columns:     2 outputs and 1 input")


def test_without_the_simulation_config_the_inputs_stay_in_the_table(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(folder=tmp_path / "results", steps=2)
    (results / "simulation.json").unlink()

    lines = output_of(passed_arguments=[str(results)], capsys=capsys)

    assert lines[4] == "Columns:     3 columns, inputs and outputs together"
    # the rows of the table, between its header and the blank line before the last line
    assert [line.split()[0] for line in lines[7:-2]] == ["house.T_room", "house.T_out_in", "weather.T_out"]


def test_the_csv_has_a_time_column_and_the_named_columns_in_the_order_of_the_names(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(folder=tmp_path / "results", steps=2)
    csv_file = tmp_path / "temperatures.csv"

    lines = output_of(passed_arguments=[str(results), "--interface", "house.T_room", "--interface", "weather", "--csv", str(csv_file)], capsys=capsys)

    assert csv_file.read_text(encoding="utf-8").splitlines() == [
        "time,house.T_room,weather.T_out",
        "2023-01-01T00:15:00+00:00,290.0,270.0",
        "2023-01-01T00:30:00+00:00,291.0,271.0",
    ]
    assert lines[-1] == f"Wrote 2 rows and 2 columns to {csv_file}."


def test_a_misspelt_interface_names_the_closest_column(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(folder=tmp_path / "results", steps=2)

    assert error_of(passed_arguments=[str(results), "--interface", "house.T_rom"], capsys=capsys) == (
        1,
        f"ecosim results: error: The results have no column house.T_rom. Did you mean house.T_room?{ONE_LINE_HINT}",
    )


def test_an_input_named_without_inputs_says_to_add_the_option(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(folder=tmp_path / "results", steps=2)

    assert error_of(passed_arguments=[str(results), "--interface", "house.T_out_in"], capsys=capsys) == (
        1,
        f"ecosim results: error: house.T_out_in is an input. Add --inputs to show inputs.{ONE_LINE_HINT}",
    )


def test_a_folder_and_the_server_config_together_are_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(folder=tmp_path / "results", steps=2)

    assert error_of(passed_arguments=[str(results), "--server-config", "preferences.ini"], capsys=capsys) == (
        2,
        "ecosim results: error: give either FOLDER or --server-config, not both",
    )


def test_database_options_without_the_server_config_are_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert error_of(passed_arguments=["--database-schema", "run_2"], capsys=capsys) == (
        2,
        "ecosim results: error: the --database options change what the server config says, so give it with --server-config",
    )


def test_a_folder_with_the_database_type_file_shows_the_files_in_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = write_results(folder=tmp_path / "results", steps=2)

    lines = output_of(passed_arguments=[str(results), "--database-type", "file"], capsys=capsys)

    assert lines[0] == f"Results:     {results}"


def test_a_folder_that_does_not_exist_names_the_closest_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "building").mkdir()

    assert error_of(passed_arguments=[str(tmp_path / "buildng")], capsys=capsys) == (
        2,
        f"ecosim results: error: the folder {tmp_path / 'buildng'} does not exist. Did you mean building?",
    )


def test_a_simulation_without_a_run_says_how_to_start_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(folder=tmp_path / "building")

    assert error_of(passed_arguments=[str(simulation)], capsys=capsys) == (
        1,
        f"ecosim results: error: {simulation} has no results yet. Run it with: ecosim run {simulation}{ONE_LINE_HINT}",
    )


def test_a_folder_with_its_results_in_a_results_folder_names_that_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    executable = tmp_path / "Executable"
    write_results(folder=executable / "results", steps=2)

    assert error_of(passed_arguments=[str(executable)], capsys=capsys)[1].endswith(
        f"The folder results in it holds result files, so run: ecosim results {executable / 'results'}{ONE_LINE_HINT}",
    )


def test_a_folder_inside_a_simulation_names_the_simulation_above_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(folder=tmp_path / "building")
    executable = simulation / "Executable"
    executable.mkdir()

    assert error_of(passed_arguments=[str(executable)], capsys=capsys) == (
        1,
        f"ecosim results: error: There are no result files in {executable}. "
        + "Give a simulation folder, a run folder, or the folder the server wrote the result files to. "
        + f"The simulation is the folder above it, so run 'ecosim results {os.path.relpath(simulation)}'.{ONE_LINE_HINT}",
    )


def test_a_folder_that_is_a_file_names_the_folder_that_holds_it(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    state_file = write_results(folder=tmp_path / "results", steps=2) / "simulation_state.jsonl"

    assert error_of(passed_arguments=[str(state_file)], capsys=capsys) == (
        2,
        f"ecosim results: error: {state_file} is a file. Give the folder that holds it: {state_file.parent}",
    )


def test_a_server_config_whose_folder_of_result_files_is_missing_says_so(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = tmp_path / "simulation_results"
    server_config = tmp_path / "preferences.ini"
    server_config.write_text(f"[server]\nport=1234\n[database]\ntype=file\ndirectory={missing}\n", encoding="utf-8")

    assert error_of(passed_arguments=["--server-config", str(server_config)], capsys=capsys) == (
        1,
        f"ecosim results: error: {missing} does not exist. A server with {server_config} writes its result files there. "
        + f"Give the folder they are in instead.{ONE_LINE_HINT}",
    )


def test_options_after_a_double_dash_say_to_leave_it_out(capsys: pytest.CaptureFixture[str]) -> None:
    passed_arguments = ["--server-config", "preferences.ini", "--", "--database-schema", "run_2"]

    assert error_of(passed_arguments=passed_arguments, capsys=capsys) == (
        2,
        "ecosim results: error: leave out the -- before the --database options. ecosim results takes them itself",
    )


def test_the_run_folder_of_a_postgres_run_says_how_to_read_postgres(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = create_simulation(folder=tmp_path / "building")
    run_folder = simulation / "results" / "2026-11-16_09-30-12"
    (run_folder / "logs").mkdir(parents=True)
    (run_folder / "simulation.json").write_text((simulation / "server" / "simulation.json").read_text(encoding="utf-8"), encoding="utf-8")

    read_command = (
        f"ecosim results --server-config {simulation / 'server' / 'preferences.ini'} --simulation-config {run_folder / 'simulation.json'} "
        + "--database-type postgres"
    )

    assert error_of(passed_arguments=[str(simulation)], capsys=capsys) == (
        1,
        f"ecosim results: error: {run_folder} holds no result files. A run with --database-type postgres stores them in PostgreSQL. "
        + f"To read them, add the --database options that the run had after -- to this command: {read_command}{ONE_LINE_HINT}",
    )


def test_a_refused_postgres_connection_ends_in_one_line_that_names_the_address(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    server_config = tmp_path / "preferences.ini"
    server_config.write_text("[server]\nport=1234\n[database]\nserver=\nport=5432\nusername=\nssl=false\n", encoding="utf-8")
    port = get_free_port()

    code, error_line = error_of(
        passed_arguments=["--server-config", str(server_config), "--database-host", "127.0.0.1", "--database-port", str(port)],
        capsys=capsys,
    )

    assert code == 1
    assert error_line.startswith(f"ecosim results: error: Cannot read the results from PostgreSQL at 127.0.0.1:{port}: ")


def test_the_database_type_option_reads_postgres_for_a_server_config_with_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    server_config = tmp_path / "preferences.ini"
    server_config.write_text("[server]\nport=1234\n[database]\ntype=file\nserver=\nport=5432\nusername=\nssl=false\n", encoding="utf-8")
    port = get_free_port()
    passed_arguments = ["--server-config", str(server_config), "--database-type", "postgres", "--database-host", "127.0.0.1"]

    code, error_line = error_of(passed_arguments=[*passed_arguments, "--database-port", str(port)], capsys=capsys)

    assert code == 1
    assert error_line.startswith(f"ecosim results: error: Cannot read the results from PostgreSQL at 127.0.0.1:{port}: ")


@skip_unless_fmpy_loads(*(BUILDING_MODULES / name / f"{name}.fmu" for name in ("house", "occupancy", "weather")))
def test_a_finished_run_names_the_command_that_reads_its_results(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = write_building_simulation(folder=tmp_path / "building")
    assert run_main(passed_arguments=[str(simulation), "--steps", "3"]) == 0
    read_command = capsys.readouterr().out.splitlines()[-1]

    assert read_command == f"Read them with: ecosim results {simulation}"
    passed_arguments = read_command.removeprefix("Read them with: ecosim results ").split()
    assert output_of(passed_arguments=passed_arguments, capsys=capsys)[1] == "Run:         finished, 3 steps of 15 min"
