import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest
from ecosim.run.run_command import main
from ecosim_common.tech.port_utils import get_free_port
from ecosim_test_common.fmpy_platform import skip_unless_fmpy_loads
from ecosim_test_common.test_data.building_simulation import BUILDING_MODULES, write_building_simulation

from tests.simulation_changes import add_room_simulator, change_json_file, interface_named, replace_in_file

pytestmark = skip_unless_fmpy_loads(*(BUILDING_MODULES / name / f"{name}.fmu" for name in ("house", "occupancy", "weather")))


@pytest.fixture
def simulation(tmp_path: Path) -> Path:
    return write_building_simulation(folder=tmp_path / "building")


def run_folders(simulation: Path) -> list[Path]:
    return sorted((simulation / "results").iterdir())


def line_count(file: Path) -> int:
    return len(file.read_text(encoding="utf-8").splitlines())


def usage_error_of(passed_arguments: list[str], capsys: pytest.CaptureFixture[str]) -> str:
    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=passed_arguments)
    assert exit_info.value.code == 2
    return capsys.readouterr().err.splitlines()[-1]


def test_the_building_simulation_runs_to_the_end_and_writes_results_and_logs(simulation: Path) -> None:
    assert main(passed_arguments=[str(simulation), "--steps", "10"]) == 0

    [run_folder] = run_folders(simulation=simulation)
    assert [line_count(file=run_folder / f"module_{name}.jsonl") for name in ("house", "occupancy", "weather")] == [10, 10, 10]
    assert sorted(log_file.name for log_file in (run_folder / "logs").iterdir()) == ["house.log", "occupancy.log", "server.log", "weather.log"]
    assert not (run_folder / "tmp").exists()


def test_a_tmp_folder_that_was_in_the_results_folder_before_the_run_is_kept(simulation: Path, tmp_path: Path) -> None:
    notes = tmp_path / "out" / "tmp" / "notes.txt"
    notes.parent.mkdir(parents=True)
    notes.write_text("my notes", encoding="utf-8")

    assert main(passed_arguments=[str(simulation), "--steps", "2", "--results", str(tmp_path / "out")]) == 0

    assert notes.read_text(encoding="utf-8") == "my notes"


def test_a_second_run_does_not_append_to_the_first(simulation: Path) -> None:
    main(passed_arguments=[str(simulation), "--steps", "10"])

    assert main(passed_arguments=[str(simulation), "--steps", "5"]) == 0

    assert [line_count(file=run_folder / "module_house.jsonl") for run_folder in run_folders(simulation=simulation)] == [10, 5]


def test_a_misspelt_input_stops_the_run_within_seconds_and_names_the_client(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    change_json_file(
        file=simulation / "server" / "simulation.json",
        change=lambda config: interface_named(simulator=config["simulators"][0], name="weatherBus_TDryBul").update(name="weatherBus_TDryBull"),
    )
    started_at = time.monotonic()

    assert main(passed_arguments=[str(simulation), "--steps", "100", "--no-check"]) == 1

    assert time.monotonic() - started_at < 20
    assert "house stopped with exit code 1." in capsys.readouterr().out


def test_a_run_without_its_length_is_a_usage_error(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert usage_error_of(passed_arguments=[str(simulation)], capsys=capsys).startswith(
        "ecosim run: error: give the length of the run with --steps or --duration",
    )


def test_a_duration_with_a_wrong_step_size_in_the_setup_names_the_step_size(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    change_json_file(file=simulation / "server" / "simulation.json", change=lambda config: config["setup"].update(delta_t="abc"))

    assert main(passed_arguments=[str(simulation), "--duration", "1d"]) == 1

    assert (
        f"  {simulation}/server/simulation.json: setup.delta_t must be a whole number of at least 1, not 'abc'."
        in capsys.readouterr().out.splitlines()
    )


def test_a_port_in_use_is_a_usage_error(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    port = get_free_port()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("localhost", port))
        listener.listen()

        error_line = usage_error_of(passed_arguments=[str(simulation), "--steps", "2", "--port", str(port)], capsys=capsys)

    assert error_line == f"ecosim run: error: localhost:{port} is in use. Leave out --port to get a free one"


def test_a_results_folder_that_holds_a_run_is_not_run_into_again(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = simulation / "results" / "first"
    results.mkdir(parents=True)
    (results / "simulation_state.jsonl").touch()

    assert usage_error_of(passed_arguments=[str(simulation), "--steps", "2", "--results", str(results)], capsys=capsys) == (
        f"ecosim run: error: {results} already holds the results of a run. "
        + "Choose another folder with --results, or continue that run with --restore-simulation-run"
    )


def test_a_pyro5_object_that_nothing_listens_on_stops_the_run_before_it_starts(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    room = add_room_simulator(simulation=simulation)
    port = get_free_port()
    replace_in_file(file=room / "preferences.ini", old="[python]\nmodel=room:Room", new=f"[pyro]\npyro_host=localhost\npyro_port={port}")

    assert main(passed_arguments=[str(simulation), "--steps", "2"]) == 1

    output = capsys.readouterr().out.splitlines()
    assert f"  {room}: nothing listens on localhost:{port} yet. Start the Pyro5 object before the run." in output
    assert output[-1] == "Found 1 problem, so nothing was started. Fix it, or start anyway with --no-check."
    assert not (simulation / "results").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="the test sends a POSIX signal to the test process")
def test_ctrl_c_stops_every_part_and_the_restore_command_continues_the_run(simulation: Path, capsys: pytest.CaptureFixture[str]) -> None:
    def press_ctrl_c_after_the_first_steps() -> None:
        while not any(line_count(file=house) > 20 for house in simulation.glob("results/*/module_house.jsonl")):
            time.sleep(0.1)
        os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=press_ctrl_c_after_the_first_steps, daemon=True).start()

    assert main(passed_arguments=[str(simulation), "--steps", "1000"]) == 33

    [run_folder] = run_folders(simulation=simulation)
    assert all("Interrupt signal received" in log_file.read_text(encoding="utf-8") for log_file in (run_folder / "logs").iterdir())
    assert json.loads((run_folder / "simulation_state.jsonl").read_text(encoding="utf-8").splitlines()[-1]) == {"state": "Failed"}
    # pgrep finds no part of the run
    assert subprocess.run(["pgrep", "-f", "--", f"-m ecosim_.*{simulation}"], check=False).returncode == 1
    restore_command = capsys.readouterr().out.splitlines()[-1].removeprefix("Continue the run with: ")
    assert restore_command == f"ecosim run {simulation} --steps 1000 --restore-simulation-run"

    assert main(passed_arguments=restore_command.split()[2:]) == 0

    assert (run_folders(simulation=simulation), line_count(file=run_folder / "module_house.jsonl")) == ([run_folder], 1000)
    assert "changed since this run started" not in capsys.readouterr().out
