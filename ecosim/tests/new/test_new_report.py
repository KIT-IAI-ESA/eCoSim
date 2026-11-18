from datetime import UTC, datetime
from pathlib import Path

from ecosim.check.simulation_check import SimulationCheck
from ecosim.new.delayed_input import DelayedInput
from ecosim.new.input_connections import InputConnections
from ecosim.new.new_report import NewReport
from ecosim.new.simulation_length import SimulationLength
from ecosim.new.simulation_model import SimulationModel
from ecosim.simulation_directory import SimulationDirectory

from tests.new.simulation_models import create_check_with_problems, create_check_without_findings, create_interface, create_model


def _report_lines(
    models: list[SimulationModel],
    given_connections: tuple[str, ...] = (),
    delays: tuple[str, ...] = (),
    check: SimulationCheck | None = None,
) -> list[str]:
    input_connections = InputConnections.of_models(models=models, given_connections=list(given_connections))
    return NewReport(
        simulation=SimulationDirectory.of_path(path=Path("my_simulation")),
        models=models,
        input_connections=input_connections,
        delayed=DelayedInput.of_texts(texts=list(delays), models=models, input_connections=input_connections),
        length=SimulationLength(step_size_in_ms=900_000, steps=96, start_date=datetime(2024, 1, 1, tzinfo=UTC), defaults=()),
        check=check or create_check_without_findings(),
    ).lines()


def test_a_connection_whose_units_differ_says_so() -> None:
    models = [
        create_model(name="house", inputs=[create_interface(name="T_out", unit="K")]),
        create_model(name="weather", outputs=[create_interface(name="T_out", unit="degC")]),
    ]

    assert any(line.endswith("(the output is in degC, the input in K)") for line in _report_lines(models=models))


def test_an_unconnected_input_suggests_the_output_with_the_closest_name() -> None:
    models = [create_model(name="house", inputs=["dir_sol_iradiance"]), create_model(name="weather", outputs=["dir_sol_irradiance", "T_out"])]

    assert (
        "  house.dir_sol_iradiance: no output of another model has this name. Did you mean weather.dir_sol_irradiance? "
        + "Then add --connect house.dir_sol_iradiance=weather.dir_sol_irradiance"
    ) in _report_lines(models=models)


def test_an_unconnected_input_suggests_no_output_that_only_shares_its_pattern() -> None:
    models = [create_model(name="house", inputs=["Float64_discrete_input"]), create_model(name="weather", outputs=["Float64_discrete_output"])]

    assert "  house.Float64_discrete_input: no output of another model has this name." in _report_lines(models=models)


def test_an_unconnected_input_shows_an_output_of_its_name_with_another_size() -> None:
    models = [create_model(name="plant", inputs=[create_interface(name="u", shape=(3,))]), create_model(name="controller", outputs=["u"])]

    assert "  plant.u: the output controller.u has this name, but it has 1 value and the input takes 3." in _report_lines(models=models)


def test_the_last_lines_are_the_commands_to_check_and_to_run_the_simulation() -> None:
    check_line, run_line = _report_lines(models=[create_model(name="weather", outputs=["T_out"])])[-2:]

    assert check_line.endswith("ecosim check my_simulation")
    assert run_line.endswith("ecosim run my_simulation")


def test_a_problem_of_the_check_is_listed_with_the_command_to_check_again() -> None:
    problem = "my_simulation/modules/weather/weather.fmu has no binary at all."

    lines = _report_lines(models=[create_model(name="weather", outputs=["T_out"])], check=create_check_with_problems(problems=[problem]))

    assert lines[0] == "Wrote my_simulation: 1 simulator, 0 connections, 1 problem."
    assert lines[-3:-1] == ["Problems:", f"  {problem}"]
    assert lines[-1].endswith("ecosim check my_simulation")


def test_a_given_and_delayed_connection_shows_its_start_value() -> None:
    models = [create_model(name="house", outputs=["room_temperature"]), create_model(name="heating", inputs=["T_room"])]

    lines = _report_lines(models=models, given_connections=("heating.T_room=house.room_temperature",), delays=("heating.T_room=293.15",))

    assert any(line.endswith("(given with --connect, one step later, starts at 293.15)") for line in lines)


def test_an_input_with_two_outputs_of_its_name_shows_how_to_choose_one() -> None:
    models = [
        create_model(name="house", inputs=["T_out"]),
        create_model(name="weather", outputs=["T_out"]),
        create_model(name="sensor", outputs=["T.out"]),
    ]

    assert "  house.T_out: 2 outputs have this name: weather.T_out and sensor.T.out. Choose one with --connect house.T_out=weather.T_out" in (
        _report_lines(models=models)
    )
