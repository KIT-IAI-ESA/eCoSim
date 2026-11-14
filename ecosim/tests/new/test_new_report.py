from datetime import UTC, datetime
from pathlib import Path

from ecosim.check.simulation_check import SimulationCheck
from ecosim.new.new_report import NewReport
from ecosim.new.simulation_length import SimulationLength
from ecosim.new.simulation_model import SimulationModel
from ecosim.new.wiring import Wiring
from ecosim.simulation_folder import SimulationFolder

from tests.new.simulation_models import create_check_with_problems, create_check_without_findings, create_interface, create_model


def _report_lines(models: list[SimulationModel], check: SimulationCheck | None = None) -> list[str]:
    return NewReport(
        simulation=SimulationFolder.of_path(path=Path("my_simulation")),
        models=models,
        wiring=Wiring.of_models(models=models),
        length=SimulationLength(step_size_in_milliseconds=900_000, steps=96, start_date=datetime(2024, 1, 1, tzinfo=UTC), defaults=()),
        check=check or create_check_without_findings(),
    ).lines()


def test_a_connection_whose_units_differ_says_so() -> None:
    models = [
        create_model(name="house", inputs=[create_interface(name="T_out", unit="K")]),
        create_model(name="weather", outputs=[create_interface(name="T_out", unit="degC")]),
    ]

    assert "    T_out  <-  T_out   (the output is in degC, the input in K)" in _report_lines(models=models)


def test_an_open_input_names_the_output_with_the_closest_name() -> None:
    models = [create_model(name="house", inputs=["dir_sol_iradiance"]), create_model(name="weather", outputs=["dir_sol_irradiance", "T_out"])]

    assert "  house.dir_sol_iradiance: no output of another model has this name. Did you mean weather.dir_sol_irradiance?" in _report_lines(
        models=models,
    )


def test_an_open_input_names_no_output_that_is_only_alike_in_its_pattern() -> None:
    models = [create_model(name="house", inputs=["Float64_discrete_input"]), create_model(name="weather", outputs=["Float64_discrete_output"])]

    assert "  house.Float64_discrete_input: no output of another model has this name." in _report_lines(models=models)


def test_an_open_input_says_when_the_output_of_its_name_holds_another_number_of_values() -> None:
    models = [create_model(name="plant", inputs=[create_interface(name="u", shape=(3,))]), create_model(name="controller", outputs=["u"])]

    assert "  plant.u: the output controller.u has this name, but it holds 1 value and the input takes 3." in _report_lines(models=models)


def test_the_last_lines_are_the_commands_to_check_and_to_run_the_simulation() -> None:
    lines = _report_lines(models=[create_model(name="weather", outputs=["T_out"])])

    assert lines[-2:] == ["After a change, check it with: ecosim check my_simulation", "Run it with: ecosim run my_simulation"]


def test_a_problem_of_the_check_is_listed_and_the_last_line_says_to_fix_it_and_check_again() -> None:
    problem = "my_simulation/Modules/weather/weather.fmu has no binary at all. Get an FMU built for linux64."

    lines = _report_lines(models=[create_model(name="weather", outputs=["T_out"])], check=create_check_with_problems(problems=[problem]))

    assert lines[0] == "Wrote my_simulation: 1 simulator, 0 connections, 1 problem."
    assert lines[-3:] == ["Problems:", f"  {problem}", "Fix it and run the check again: ecosim check my_simulation"]
