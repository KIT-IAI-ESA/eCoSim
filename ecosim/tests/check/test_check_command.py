import logging
from pathlib import Path

import pytest
from ecosim.check.check_command import main
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_test_common.test_data.building_simulation import write_building_simulation

from tests.command_errors import error_of
from tests.simulation_changes import replace_in_file


def test_problems_end_with_the_failed_exit_code_and_show_their_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = write_building_simulation(directory=tmp_path / "building")
    replace_in_file(file=simulation / "modules" / "house" / "preferences.ini", old="simulator_name=house", new="simulator_name=hous")

    assert main(passed_arguments=[str(simulation)]) == ShutdownManager.FAILED_RUN_EXIT_CODE

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "Checked building: 2 simulators, 1 problem."
    assert lines[lines.index("Problems:") + 1].startswith(f"  {simulation}/modules/house/preferences.ini: simulator_name is 'hous'")
    assert lines[-1].startswith("Fix it and run the check again: ")
    assert lines[-1].endswith(f"ecosim check {simulation}")


def test_warnings_alone_end_with_the_success_exit_code(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = write_building_simulation(directory=tmp_path / "building")
    replace_in_file(file=simulation / "server" / "simulation.json", old='"setup": {', new='"comment": "first try",\n  "setup": {')

    assert main(passed_arguments=[str(simulation), "--steps", "100"]) == ShutdownManager.SUCCESS_EXIT_CODE

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "Checked building: 3 simulators, no problems, 1 warning."
    assert "Warnings:" in lines


def test_the_length_of_the_run_is_shown_only_when_it_is_known(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = write_building_simulation(directory=tmp_path / "building")

    main(passed_arguments=[str(simulation)])
    lines_without_a_length = capsys.readouterr().out.splitlines()
    main(passed_arguments=[str(simulation), "--steps", "100"])
    lines_with_a_length = capsys.readouterr().out.splitlines()

    assert lines_without_a_length[1].startswith("  house")
    assert lines_with_a_length[1].startswith("100 steps of 15 min")


def test_with_debug_the_check_logs_nothing_of_the_readers(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    simulation = write_building_simulation(directory=tmp_path / "building")
    caplog.set_level(logging.DEBUG)

    main(passed_arguments=[str(simulation), "--steps", "100", "--debug"])

    assert caplog.messages == []


def test_a_directory_that_is_not_a_simulation_is_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code, error_line = error_of(arguments=["check", str(tmp_path)], capsys=capsys)

    assert exit_code == USAGE_ERROR_EXIT_CODE
    assert error_line.startswith(f"ecosim check: error: {tmp_path.name} is not a simulation folder.")
