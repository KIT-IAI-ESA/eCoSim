import logging
from pathlib import Path

import pytest
from ecosim.check.check_command import main
from ecosim_test_common.test_data.building_simulation import write_building_simulation

from tests.simulation_changes import replace_in_file


def test_problems_exit_with_1_and_name_their_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = write_building_simulation(folder=tmp_path / "building")
    replace_in_file(file=simulation / "Modules" / "house" / "preferences.ini", old="simulator_name=house", new="simulator_name=hous")

    assert main(passed_arguments=[str(simulation)]) == 1

    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "Checked building: 2 simulators, 1 problem."
    assert lines[lines.index("Problems:") + 1].startswith(f"  {simulation}/Modules/house/preferences.ini: simulator_name is 'hous'")
    assert lines[-1] == f"Fix it and run the check again: ecosim check {simulation}"


def test_warnings_alone_exit_with_0(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    simulation = write_building_simulation(folder=tmp_path / "building")
    replace_in_file(file=simulation / "server" / "simulation.json", old='"setup": {', new='"comment": "first try",\n  "setup": {')

    assert main(passed_arguments=[str(simulation), "--steps", "100"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[:2] == [
        "Checked building: 3 simulators, no problems, 1 warning.",
        "100 steps of 15 min, from 2023-01-01 00:00 to 2023-01-02 01:00 UTC.",
    ]
    assert "Warnings:" in lines


def test_with_debug_the_check_logs_nothing_of_the_readers(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    simulation = write_building_simulation(folder=tmp_path / "building")
    caplog.set_level(logging.DEBUG)

    assert main(passed_arguments=[str(simulation), "--steps", "100", "--debug"]) == 0

    assert caplog.messages == []


def test_a_folder_that_is_no_simulation_is_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=[str(tmp_path)])

    assert exit_info.value.code == 2
    assert (
        capsys.readouterr().err.splitlines()[-1]
        == f"ecosim check: error: {tmp_path.name} is not a simulation folder: it has no server/simulation.json."
    )
