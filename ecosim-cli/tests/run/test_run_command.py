import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim.run.run_command import main
from ecosim_common.tech.port_utils import get_free_port
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_test_common.test_data.building_simulation import BUILDING_SIMULATORS, skip_unless_fmpy_loads_the_building_fmus, write_building_simulation

from tests.command_errors import error_of
from tests.simulation_changes import add_room_simulator, change_json_file, interface_named, replace_in_file

pytestmark = skip_unless_fmpy_loads_the_building_fmus()


@pytest.fixture
def simulation(tmp_path: Path) -> Path:
    return write_building_simulation(directory=tmp_path / "building")


def run_directories(simulation: Path) -> list[Path]:
    return sorted((simulation / "results").iterdir())


def line_count(file: Path) -> int:
    return len(file.read_text(encoding="utf-8").splitlines())


def test_the_building_simulation_runs_to_the_end_and_writes_results_and_logs(simulation: Path) -> None:
    assert main(passed_arguments=[str(simulation), "--steps", "10"]) == ShutdownManager.SUCCESS_EXIT_CODE

    [run_directory] = run_directories(simulation=simulation)
    assert [line_count(file=run_directory / f"module_{name}.jsonl") for name in BUILDING_SIMULATORS] == [10, 10, 10]
    assert sorted(log_file.stem for log_file in (run_directory / "logs").iterdir()) == sorted(["server", *BUILDING_SIMULATORS])


def test_the_tmp_directory_of_a_run_is_removed_at_its_end(simulation: Path) -> None:
    main(passed_arguments=[str(simulation), "--steps", "2"])

    [run_directory] = run_directories(simulation=simulation)
    assert not (run_directory / "tmp").exists()


def test_a_tmp_directory_that_was_in_the_results_directory_before_the_run_is_kept(simulation: Path, tmp_path: Path) -> None:
    notes = tmp_path / "out" / "tmp" / "notes.txt"
    notes.parent.mkdir(parents=True)
    notes.write_text("my notes", encoding="utf-8")

    main(passed_arguments=[str(simulation), "--steps", "2", "--results", str(tmp_path / "out")])

    assert notes.read_text(encoding="utf-8") == "my notes"


def test_a_second_run_does_not_append_to_the_first(simulation: Path) -> None:
    main(passed_arguments=[str(simulation), "--steps", "10"])

    main(passed_arguments=[str(simulation), "--steps", "5"])

    assert [line_count(file=run_directory / "module_house.jsonl") for run_directory in run_directories(simulation=simulation)] == [10, 5]


def test_a_misspelled_input_stops_the_run_within_seconds_and_shows_the_client(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    change_json_file(
        file=simulation / "server" / "simulation.json",
        change=lambda config: interface_named(simulator=config["simulators"][0], name="weatherBus_TDryBul").update(name="weatherBus_TDryBull"),
    )
    started_at = time.monotonic()

    assert main(passed_arguments=[str(simulation), "--steps", "100", "--no-check"]) == ShutdownManager.FAILED_RUN_EXIT_CODE

    assert time.monotonic() - started_at < 20
    assert "house stopped with exit code 1." in capsys.readouterr().out


def test_a_run_without_its_length_is_a_usage_error(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, error_line = error_of(arguments=["run", str(simulation)], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line == (
        'ecosim run: error: set the length of the run with --steps or --duration, or add "steps" to setup in '
        + f"{simulation / 'server' / 'simulation.json'}"
    )


def test_a_duration_with_a_wrong_step_size_in_the_setup_is_a_problem_of_delta_t(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    change_json_file(file=simulation / "server" / "simulation.json", change=lambda config: config["setup"].update(delta_t="abc"))

    assert main(passed_arguments=[str(simulation), "--duration", "1d"]) == ShutdownManager.FAILED_RUN_EXIT_CODE

    [problem] = [line for line in capsys.readouterr().out.splitlines() if line.startswith(f"  {simulation}")]
    assert "setup.delta_t" in problem


def test_a_port_in_use_is_a_usage_error(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    port = get_free_port()
    with socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM) as listener:
        listener.bind(("localhost", port))
        listener.listen()

        exit_code, error_line = error_of(arguments=["run", str(simulation), "--steps", "2", "--port", str(port)], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line == f"ecosim run: error: localhost:{port} is in use. Leave out --port to get a free one"


def test_a_results_directory_with_a_run_is_not_run_into_again(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = simulation / "results" / "first"
    results.mkdir(parents=True)
    (results / "simulation_state.jsonl").touch()

    exit_code, error_line = error_of(arguments=["run", str(simulation), "--steps", "2", "--results", str(results)], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line == (
        f"ecosim run: error: {results} already contains the results of a run. "
        + "Choose another folder with --results, or continue that run with --restore-simulation-run"
    )


def test_a_pyro5_object_that_nothing_listens_on_stops_the_run_before_it_starts(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    room = add_room_simulator(simulation=simulation)
    replace_in_file(
        file=room / "preferences.ini",
        old="[python]\nmodel=room:Room",
        new=f"[pyro]\npyro_host=localhost\npyro_port={get_free_port()}",
    )

    assert main(passed_arguments=[str(simulation), "--steps", "2"]) == ShutdownManager.FAILED_RUN_EXIT_CODE

    assert capsys.readouterr().out.splitlines()[-1] == "Found 1 problem. Nothing was started. Use --no-check to start anyway."
    assert not (simulation / "results").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no SIGINT for another process")
def test_the_restore_command_continues_a_run_that_ctrl_c_stopped(simulation: Path) -> None:
    # without UV the printed command starts with ecosim
    environment = {name: value for name, value in os.environ.items() if name != "UV"}
    command = [sys.executable, "-m", "ecosim.main", "run", str(simulation), "--steps", "1000"]
    run = subprocess.Popen(command, env=environment, stdout=subprocess.PIPE, text=True)
    while run.poll() is None and not any(line_count(file=house) > 20 for house in simulation.glob("results/*/module_house.jsonl")):
        time.sleep(0.1)

    run.send_signal(signal.SIGINT)
    output, _ = run.communicate()

    assert run.returncode == ShutdownManager.INTERRUPT_EXIT_CODE
    restore_command = output.splitlines()[-1].removeprefix("Continue the run with: ecosim run ")
    assert restore_command == f"{simulation} --steps 1000 --restore-simulation-run"

    assert main(passed_arguments=restore_command.split()) == ShutdownManager.SUCCESS_EXIT_CODE

    [run_directory] = run_directories(simulation=simulation)
    assert line_count(file=run_directory / "module_house.jsonl") == 1000
