import json
from pathlib import Path
from typing import Any

import fmpy
import pytest
from ecosim_common.config.argument_parser import USAGE_ERROR_EXIT_CODE
from ecosim.new.new_command import main
from ecosim_common.tech.shutdown_manager import ShutdownManager
from ecosim_server.measurement.postgres_name_check import MAXIMUM_SIMULATOR_NAME_IN_BYTES
from ecosim_test_common.resources.resource_utils import fmu2_model_path, resource_path_file
from ecosim_test_common.test_data.generate_changed_fmu import generate_fmu_without_binaries_for


def _setup_of(simulation: Path) -> dict[str, Any]:
    setup: dict[str, Any] = json.loads((simulation / "server" / "simulation.json").read_text(encoding="utf-8"))["setup"]
    return setup


def test_the_duration_becomes_the_steps_of_the_setup(tmp_path: Path) -> None:
    main(passed_arguments=[str(tmp_path / "simulation"), str(fmu2_model_path()), "--duration", "1y"])

    assert _setup_of(simulation=tmp_path / "simulation") | {"start_date": None} == {"delta_t": 900_000, "steps": 35_040, "start_date": None}


def test_a_start_date_without_an_offset_is_utc(tmp_path: Path) -> None:
    main(passed_arguments=[str(tmp_path / "simulation"), str(fmu2_model_path()), "--start-date", "2023-01-01T06:00"])

    assert _setup_of(simulation=tmp_path / "simulation")["start_date"] == "2023-01-01T06:00:00+00:00"


def test_the_report_marks_the_values_that_are_defaults(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    main(passed_arguments=[str(tmp_path / "simulation"), str(fmu2_model_path())])

    assert capsys.readouterr().out.splitlines()[2] == (
        "The step size 15min, the length 1d and the start date 2024-01-01 are the defaults. "
        + "Choose others with --step-size, --duration and --start-date."
    )


def test_a_directory_that_is_not_empty_is_left_unchanged(tmp_path: Path) -> None:
    (tmp_path / "simulation").mkdir()
    (tmp_path / "simulation" / "notes.txt").write_text("mine", encoding="utf-8")

    with pytest.raises(ValueError, match="simulation already exists and is not empty"):
        main(passed_arguments=[str(tmp_path / "simulation"), str(fmu2_model_path())])

    assert [path.name for path in (tmp_path / "simulation").iterdir()] == ["notes.txt"]


def test_a_duration_of_no_whole_number_of_steps_is_a_usage_error_and_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=[str(tmp_path / "simulation"), str(fmu2_model_path()), "--step-size", "7min", "--duration", "1h"])

    assert exit_info.value.code == USAGE_ERROR_EXIT_CODE
    assert list(tmp_path.iterdir()) == []


def test_a_date_that_does_not_exist_is_a_usage_error_with_an_example(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=["simulation", "model.fmu", "--start-date", "2023-13-01"])

    assert exit_info.value.code == USAGE_ERROR_EXIT_CODE
    assert (
        capsys.readouterr().err.splitlines()[-1]
        == "ecosim new: error: argument --start-date: must be a date like 2023-01-01 or 2023-01-01T06:00+01:00, not '2023-13-01'"
    )


def test_a_step_size_that_does_not_divide_the_default_length_is_a_usage_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(passed_arguments=[str(tmp_path / "simulation"), str(fmu2_model_path()), "--step-size", "7min"])

    assert exit_info.value.code == USAGE_ERROR_EXIT_CODE
    assert capsys.readouterr().err.splitlines()[-1].startswith("ecosim new: error: The default length 1d is not a whole number of steps of 7 min.")


def test_a_problem_of_the_check_keeps_the_simulation_and_fails_the_command(tmp_path: Path) -> None:
    fmu_file = generate_fmu_without_binaries_for(fmu_file=fmu2_model_path(), directory=tmp_path, platform=fmpy.platform)

    assert main(passed_arguments=[str(tmp_path / "simulation"), str(fmu_file)]) == ShutdownManager.FAILED_RUN_EXIT_CODE

    assert (tmp_path / "simulation" / "server" / "simulation.json").is_file()


def test_a_model_name_too_long_for_postgres_is_rejected_and_nothing_is_written(tmp_path: Path) -> None:
    long_name = "a" * (MAXIMUM_SIMULATOR_NAME_IN_BYTES + 1)

    with pytest.raises(ValueError) as error:
        main(passed_arguments=[str(tmp_path / "simulation"), f"{long_name}={fmu2_model_path()}", "--database-type", "postgres"])

    assert str(error.value) == (
        f"The model name {long_name} has {len(long_name)} characters, but PostgreSQL takes at most {MAXIMUM_SIMULATOR_NAME_IN_BYTES}. "
        + f"Use a shorter name, like {long_name[:16]}={fmu2_model_path()}"
    )
    assert list(tmp_path.iterdir()) == []


def test_new_writes_nothing_when_a_loop_is_left_open(tmp_path: Path) -> None:
    # the model descriptions are the same in the builds of every platform
    house_fmus = resource_path_file("fmu_v2/models/house/linux")
    connections = [
        "--connect",
        "heating.T_room=house.room_temperature",
        "--connect",
        "house.heating_heatExchanger_control_signal=heating.heating_control_signal",
    ]

    with pytest.raises(ValueError, match="heating and house form a loop"):
        main(passed_arguments=[str(tmp_path / "simulation"), str(house_fmus / "house.fmu"), str(house_fmus / "heating.fmu"), *connections])

    assert list(tmp_path.iterdir()) == []
